"""
This module provides a wrapper around an
`RPyC <https://rpyc.readthedocs.io/en/latest/>`__ server. Clients may connect and
access devices, or command the server to add, remove, or restart devices.
"""
import logging
import threading
import time
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

from rpyc import ClassicService
from rpyc.core.protocol import Connection
from rpyc.utils.classic import obtain
from rpyc.utils.server import ThreadedServer

from ..misc.misc import _load_class_from_file
from ..misc.misc import _load_class_from_str

try:
    from ..misc.pint import Q_
    from ..misc.pint import register_quantity_brining
except ImportError:
    pass
else:
    # monkey-patch fix for pint module
    register_quantity_brining(Q_)

_logger = logging.getLogger(__name__)

INSTRUMENT_SERVER_DEFAULT_PORT = 42068
"""Default instrument server port."""

RPYC_SYNC_TIMEOUT = 30
"""RPyC send/receive timeout in seconds (don't set to None)."""

# event used for waiting until the rpyc server thread has finished
_RPYC_SERVER_STOP_EVENT = threading.Event()


class InstrumentServerError(Exception):
    """Raised for failures related to the
    :py:class:`~nspyre.instrument.server.InstrumentServer`."""

    def __init__(self, *args, **kwargs):
        """
        Args:
            args: Arguments to pass to super class Exception().
            kwargs: Keyword arguments to pass to super class Exception().
        """
        # override this so that the docs don't the print superclass docstring
        super().__init__(*args, **kwargs)


class InstrumentServerDeviceExistsError(InstrumentServerError):
    """Raised if attempting to add a device that already exists to the
    :py:class:`~nspyre.instrument.server.InstrumentServer`."""

    def __init__(self, *args, **kwargs):
        """
        Args:
            args: Arguments to pass to super class Exception().
            kwargs: Keyword arguments to pass to super class Exception().
        """
        # override this so that the docs don't the print superclass docstring
        super().__init__(*args, **kwargs)


class InstrumentServer(ClassicService):
    """RPyC service that loads devices and exposes them to the client.

    The `RPyC <https://rpyc.readthedocs.io/en/latest/>`__ service starts a new
    thread running an RPyC server. Clients may connect and access devices or
    command the server to add, remove, or restart devices (through the
    :py:class:`~nspyre.instrument.gateway.InstrumentGateway`).

    """

    def __init__(
        self,
        port: int = INSTRUMENT_SERVER_DEFAULT_PORT,
        sync_timeout: float = RPYC_SYNC_TIMEOUT,
    ):
        """
        Args:
            port: Port number to use for the RPyC server.
            sync_timeout: Time to wait for requests / function calls to finish.
        """

        super().__init__()
        # dictionary where keys are the device names, values are tuples:
        # (device object, device configuration settings dictionary)
        self._devs: Dict[str, Any] = {}
        # rpyc server port
        self._port = port
        self._sync_timeout = sync_timeout
        # rpyc server
        self._rpyc_server = None

    def add(
        self,
        name: str,
        class_path: str,
        class_name: str,
        args: Optional[list] = None,
        kwargs: Optional[Dict] = None,
        import_or_file: str = 'file',
        local_args: bool = False,
    ):
        """Create an instance of the specified class and add it to the instrument
        server.

        Args:
            name: Alias for the device.
            class_path: If import_or_file is :code:`'file'`, path to the file on
                the filesystem containing the class, e.g.
                :code:`'~/drivers/rohde_schwarz/hmp4040.py'`. If import_or_file
                is :code:`'import'`, python module containing the class, e.g.
                :code:`'nspyre_drivers.rohde_schwarz.hmp4040.hmp4040'`.
            class_name: Name of the class to create an instance of, e.g.
                :code:`'HMP4040'`.
            args: Arguments to pass to :code:`class_name.__init__`.
            kwargs: Keyword arguments to pass to :code:`class_name.__init__`..
            import_or_file: :code:`'file'` for creating the device object from
                a file on the filesystem, :code:`'import'` for creating the
                device object from a python module.
            local_args: If True, all arguments to this method are assumed to be
                local variables not passed through an
                :py:class:`~nspyre.instrument.gateway.InstrumentGateway`. In
                this case, the arguments will be taken as-is. If False, all
                arguments will be retrieved using rpyc.utils.classic.obtain
                in order to ensure they are not netrefs.

        Raises:
            ValueError: An argument was invalid.
            InstrumentServerDeviceExistsError: Tried to add a device that already
                exists.
            InstrumentServerError: Anything else.
        """
        if not local_args:
            # make sure that the arguments actually exist on the local machine
            # and are not netrefs - otherwise there could be dangling references
            # left over in the self._devs dictionary after the client disconnects
            name = obtain(name)
            class_path = obtain(class_path)
            class_name = obtain(class_name)
            import_or_file = obtain(import_or_file)
            try:
                args = obtain(args)
                kwargs = obtain(kwargs)
            except TypeError as err:
                raise InstrumentServerError(
                    'The args or kwargs could not be '
                    'obtained with rpyc. They may contain unpickleable '
                    'objects. If the call to add() is being made on the local '
                    'machine, you can use local_args = True.'
                ) from err

        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}

        if name in self._devs:
            raise InstrumentServerDeviceExistsError(
                f'Device [{name}] already exists on the InstrumentServer.'
            )

        if import_or_file == 'file':
            # load the class from a file on disk
            try:
                dev_class_path = Path(class_path).resolve()
                dev_class = _load_class_from_file(dev_class_path, class_name)
            except Exception as exc:
                raise InstrumentServerError(
                    f'The specified class [{class_name}] from file [{class_path}] for'
                    f' device [{name}] couldn\'t be loaded.'
                ) from exc
        elif import_or_file == 'import':
            # load the class from a python module
            try:
                dev_class_mod = f'{class_path}.{class_name}'
                dev_class = _load_class_from_str(dev_class_mod)
            except Exception as exc:
                raise InstrumentServerError(
                    f'The specified class [{dev_class_mod}] for device [{name}]'
                    ' couldn\'t be loaded.',
                ) from exc
        else:
            raise ValueError(
                'Argument import_or_file must be "file" or "import"; got'
                f' [{import_or_file}].'
            )

        # create an instance of the device
        try:
            instance = dev_class(*args, **kwargs)
        except Exception as exc:
            raise InstrumentServerError(
                f'Failed to create an instance of device [{name}] of class'
                f' [{dev_class}].',
            ) from exc

        # initialize the driver if it implements an __enter__ function
        if hasattr(instance, '__enter__'):
            instance.__enter__()

        # save the device and config info
        config = {
            'class_path': class_path,
            'class_name': class_name,
            'import_or_file': import_or_file,
            'args': args,
            'kwargs': kwargs,
            'local_args': local_args,
        }
        self._devs[name] = (instance, config)

        _logger.info(f'Added device [{name}] with args: {args} kwargs: {kwargs}.')

    def remove(self, name: str):
        """Remove a device from the instrument server.

        Args:
            name: Alias for the device.

        Raises:
            InstrumentServerError: Deleting the device failed.
        """
        try:
            dev, _ = self._devs.pop(name)
        except Exception as exc:
            raise InstrumentServerError(f'Failed deleting device [{name}].') from exc

        # teardown the driver if it implements an __exit__ function
        if hasattr(dev, '__exit__'):
            dev.__exit__(None, None, None)

        _logger.info(f'Deleted device [{name}].')

    def restart(self, name: str):
        """Restart the specified device by deleting it and creating a new instance.

        Args:
            name: Alias for the device.

        Raises:
            InstrumentServerError: Deleting the device failed.
        """
        config_dict = self._devs[name][1]
        self.remove(name)
        self.add(name, **config_dict)

    def restart_all(self):
        """Restart all devices on the server.

        Raises:
            InstrumentServerError: Deleting a device failed.
        """
        for d in list(self._devs):
            self.restart(d)

    def start(self):
        """Start the RPyC server.

        Raises:
            InstrumentServerError: The server was already running.
        """
        if self._rpyc_server:
            raise InstrumentServerError(
                'Can\'t start the RPyC server because one is already running.'
            )
        thread = threading.Thread(target=self._rpyc_server_thread)
        thread.start()
        # wait for the server to start
        while not (self._rpyc_server and self._rpyc_server.active):
            time.sleep(0.1)

    def _rpyc_server_thread(self):
        """Thread for running the RPyC server asynchronously"""
        _logger.info('Starting InstrumentServer RPyC server...')
        self._rpyc_server = ThreadedServer(
            self,
            hostname='127.0.0.1',
            port=self._port,
            protocol_config={
                'allow_pickle': True,
                'allow_all_attrs': True,
                'allow_setattr': True,
                'allow_delattr': True,
                'sync_request_timeout': self._sync_timeout,
                'import_custom_exceptions': True,
            },
        )
        self._rpyc_server.start()
        _logger.info('RPyC server stopped.')
        _RPYC_SERVER_STOP_EVENT.set()

    def stop(self):
        """Stop the RPyC server.

        Raises:
            InstrumentServerError: The server wasn't running.
        """
        if not self._rpyc_server:
            raise InstrumentServerError(
                'Can\'t stop the RPyC server because there isn\'t one running.'
            )

        _logger.info('Removing devices...')
        for d in list(self._devs):
            self.remove(d)

        _logger.info('Stopping RPyC server...')
        self._rpyc_server.close()
        _RPYC_SERVER_STOP_EVENT.wait()
        _RPYC_SERVER_STOP_EVENT.clear()
        self._rpyc_server = None

    def devs(self):
        """Return all of the devices on the InstrumentSever.

        Returns:
            dict: The device names as keys and device objects as values.
        """
        devs = {}
        for d in self._devs:
            devs[d] = getattr(self, d)
        return devs

    def __getattr__(self, attr: str):
        """Allow the user to access the driver objects directly using
        server.device.attribute notation e.g. local_server.sig_gen.amplitude = 5

        Args:
            attr: Alias for the device.
        """
        if attr in self._devs:
            return self._devs[attr][0]
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)

    def on_connect(self, conn: Connection):
        """Called when a client connects to the RPyC server."""
        _logger.info(f'Client {conn} connected.')

    def on_disconnect(self, conn: Connection):
        """Called when a client disconnects from the RPyC server."""
        _logger.info(f'Client {conn} disconnected.')

    def __enter__(self):
        """Python context manager setup"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.stop()
