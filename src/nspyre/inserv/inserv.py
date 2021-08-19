"""
This module starts a process running an RPyC server. Clients may connect and access devices, or command the server to add, remove, or restart devices.

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
import threading
import time
from pathlib import Path

from rpyc import ClassicService
from rpyc.utils.classic import obtain
from rpyc.utils.server import ThreadedServer

from ..misc.misc import load_class_from_file
from ..misc.misc import load_class_from_str
from ..misc.pint import Q_
from ..misc.pint import register_quantity_brining

# monkey-patch fix for pint module
register_quantity_brining(Q_)

logger = logging.getLogger(__name__)

# default instrument server port
INSERV_DEFAULT_PORT = 42068

# rpyc send/receive timeout in s (don't set to None)
RPYC_SYNC_TIMEOUT = 30

# event used for waiting until the rpyc server thread has finished
RPYC_SERVER_STOP_EVENT = threading.Event()


class InstrumentServerError(Exception):
    """Raised for failures related to the InstrumentServer."""


class InstrumentServerDeviceExistsError(InstrumentServerError):
    """Raised if attempting to add a device that already exists to the InstrumentServer."""


class InstrumentServer(ClassicService):
    """RPyC service that loads devices and exposes them to the client.

    The RPyC service (https://rpyc.readthedocs.io/en/latest/) starts a new thread running an RPyC server. Clients may connect and access devices or command the server to add, remove, or restart devices (through the InstrumentGateway).

    Typical usage example:

    .. code-block:: python

        from nspyre import InstrumentServer, InstrumentServerDeviceExistsError, InstrumentGateway, InstrumentGatewayError

        port = 4000

        # first try connecting to an existing instrument server, if one is already running
        try:
            inserv = InstrumentGateway(port=port)
            inserv.connect()
        except InstrumentGatewayError:
            # if no server was running, start one
            inserv = InstrumentServer(port=port)
            inserv.start()

        # add some devices to the server (if they aren't already added)

        # sig gen
        try:
            inserv.add('sg', '~/my_project/drivers/siggen.py', 'SigGen')
        except InstrumentServerDeviceExistsError:
            pass

        # NI DAQ
        try:
            inserv.add('daq', '~/my_project/drivers/daq.py', 'NIDAQ')
        except InstrumentServerDeviceExistsError:
            pass

        # flip pellicle
        try:
            inserv.add('pel', '~/my_project/drivers/flip_pel.py', 'FlipPellicle')
        except InstrumentServerDeviceExistsError:
            pass

        while True:
            time.sleep(1)

    """

    def __init__(self, port=INSERV_DEFAULT_PORT):
        """Initialize an instrument server.

        Args:
            port: port number to use for the RPyC server
        """

        super().__init__()
        # dictionary where keys are the device names, values are tuples:
        # (device object, device configuration settings dictionary)
        self.devs = {}
        # rpyc server port
        self.port = port
        # rpyc server
        self._rpyc_server = None

    def add(
        self,
        name: str,
        class_path: str,
        class_name: str,
        *args,
        import_or_file: str = 'file',
        **kwargs,
    ):
        r"""Create an instance of the specified class and add it to the instrument server.

        Args:
            name: Alias for the device.
            class_path: If import_or_file is 'file', path to the file containing the class, e.g. '~/drivers/oscilloscopes/rtb2004.py'. If import_or_file is 'import', python module containing the class, e.g. 'driver_module.oscilloscopes.rtb2004'
            class_name: Name of the class to create an instance of, e.g. 'RTB2004'.
            import_or_file: 'file' for creating the device object from a file on disk, 'import' for creating the device object from a python module.
            args: arguments to pass to the class during initialization, as in RTB2004(\*args, \*\*kwargs).
            kwargs: keyword args to pass to the class during initialization, as in RTB2004(\*args, \*\*kwargs).

        Raises:
            ValueError: An argument was invalid.
            InstrumentServerDeviceExistsError: Tried to add a device that already exists.
            InstrumentServerError: Anything else.
        """

        # make sure that the arguments actually exist on the local machine
        # and are not netrefs - otherwise there could be dangling references left over
        # in the self.devs dictionary after the client disconnects
        name = obtain(name)
        class_path = obtain(class_path)
        class_name = obtain(class_name)
        import_or_file = obtain(import_or_file)
        args = obtain(args)
        kwargs = obtain(kwargs)

        if name in self.devs:
            raise InstrumentServerDeviceExistsError(f'device "{name}" already exists')

        if import_or_file == 'file':
            # load the class from a file on disk
            try:
                dev_class_path = Path(class_path).resolve()
                dev_class = load_class_from_file(dev_class_path, class_name)
            except Exception as exc:
                raise InstrumentServerError(
                    f'The specified class "{class_name}" from file "{class_path}" for'
                    f' device "{name}" couldn\'t be loaded'
                ) from exc
        elif import_or_file == 'import':
            # load the class from a python module
            try:
                dev_class_mod = f'{class_path}.{class_name}'
                dev_class = load_class_from_str(dev_class_mod)
            except Exception as exc:
                raise InstrumentServerError(
                    f'The specified class "{dev_class_mod}" for device "{name}"'
                    ' couldn\'t be loaded',
                ) from exc
        else:
            raise ValueError(
                'argument import_or_file must be "file" or "import"; got'
                f' "{import_or_file}"'
            )

        # create an instance of the device
        try:
            instance = dev_class(*args, **kwargs)
        except Exception as exc:
            raise InstrumentServerError(
                f'Failed to create an instance of device "{name}" of class'
                f' "{dev_class}"',
            ) from exc

        # save the device and config info
        config = {
            'class_path': class_path,
            'class_name': class_name,
            'import_or_file': import_or_file,
            'args': args,
            'kwargs': kwargs,
        }
        self.devs[name] = (instance, config)

        logger.info(f'added device "{name}" with args: {args} kwargs: {kwargs}')

    def remove(self, name):
        """Remove a device from the instrument server.

        Args:
            name: Alias for the device.

        Raises:
            InstrumentServerError: Deleting the device failed.
        """
        try:
            self.devs.pop(name)
        except Exception as exc:
            raise InstrumentServerError(f'Failed deleting device "{name}"') from exc
        logger.info(f'deleted device "{name}"')

    def restart(self, name: str):
        """Restart the specified device by deleting it and creating a new instance.

        Args:
            name: Alias for the device.

        Raises:
            InstrumentServerError: Deleting the device failed.
        """
        config_dict = self.devs[name][1]
        class_path = config_dict['class_path']
        class_name = config_dict['class_name']
        args = config_dict['args']
        import_or_file = config_dict['import_or_file']
        kwargs = config_dict['kwargs']
        self.remove(name)
        self.add(
            name,
            class_path,
            class_name,
            *args,
            import_or_file=import_or_file,
            **kwargs,
        )

    def restart_all(self):
        """Restart all devices on the server.

        Raises:
            InstrumentServerError: Deleting a device failed.
        """
        for d in self.devs:
            self.restart_device(d)

    def start(self):
        """Start the RPyC server.

        Raises:
            InstrumentServerError: The server was already running.
        """
        if self._rpyc_server:
            raise InstrumentServerError(
                'Can\'t start the rpyc server because one is already running.'
            )
        thread = threading.Thread(target=self._rpyc_server_thread)
        thread.start()
        # wait for the server to start
        while not (self._rpyc_server and self._rpyc_server.active):
            time.sleep(0.1)

    def _rpyc_server_thread(self):
        """Thread for running the RPyC server asynchronously"""
        logger.info('starting InstrumentServer RPyC server...')
        self._rpyc_server = ThreadedServer(
            self,
            port=self.port,
            protocol_config={
                'allow_pickle': True,
                'allow_all_attrs': True,
                'allow_setattr': True,
                'allow_delattr': True,
                'sync_request_timeout': RPYC_SYNC_TIMEOUT,
            },
        )
        self._rpyc_server.start()
        logger.info('RPyC server stopped')
        RPYC_SERVER_STOP_EVENT.set()

    def stop(self):
        """Stop the RPyC server.

        Raises:
            InstrumentServerError: The server wasn't running.
        """
        if not self._rpyc_server:
            raise InstrumentServerError(
                'Can\'t stop the rpyc server because there isn\'t one running.'
            )

        logger.info('stopping RPyC server...')
        self._rpyc_server.close()
        RPYC_SERVER_STOP_EVENT.wait()
        RPYC_SERVER_STOP_EVENT.clear()
        self._rpyc_server = None

    def __getattr__(self, attr: str):
        """Allow the user to access the driver objects directly using
        server.device.attribute notation e.g. local_server.sig_gen.amplitude = 5

        Args:
            attr: Alias for the device.
        """
        if attr in self.devs:
            return self.devs[attr][0]
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)

    def on_connect(self, conn):
        """Called when a client connects to the RPyC server"""
        logger.info(f'client {conn} connected')

    def on_disconnect(self, conn):
        """Called when a client disconnects from the RPyC server"""
        logger.info(f'client {conn} disconnected')

    def __enter__(self):
        """Python context manager setup"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.stop()
