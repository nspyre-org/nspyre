"""
This module allows interfacing with an instrument server.

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
import time

import rpyc

try:
    from ..misc.pint import Q_
    from ..misc.pint import register_quantity_brining
except ImportError:
    pass
else:
    # monkey-patch fix for pint module
    register_quantity_brining(Q_)
from .inserv import INSERV_DEFAULT_PORT
from .inserv import RPYC_SYNC_TIMEOUT

logger = logging.getLogger(__name__)

# rpyc connection timeout in s (None for no timeout)
RPYC_CONN_TIMEOUT = 30


class InstrumentGatewayError(Exception):
    """Raised for failures related to the Instrument Gateway."""


class InstrumentGateway:
    """Create a connection to an InstrumentServer and access it's devices.

    Typical usage example:

        First start the instrument server from the console on machine A:

        .. code-block:: console

            $ nspyre-inserv

        Then run the following python program on machine B:

        .. code-block:: python

            from nspyre import InstrumentGateway

            # machine A ip address = '192.168.1.20'
            with InstrumentGateway(addr='192.168.1.20') as gw:
                try:
                    # machine A must contain a python file at this location containing a class with the name "SigGen"
                    gw.add('sg', '~/my_project/drivers/sig_gen.py', 'SigGen')
                except InstrumentServerDeviceExistsError:
                    # the device has already been added to the instrument server
                    pass
                try:
                    # machine A must contain a python file at this location containing a class with the name "Multimeter"
                    gw.add('multimeter', '~/my_project/drivers/meter.py', 'Multimeter')
                except InstrumentServerDeviceExistsError:
                    # the device has already been added to the instrument server
                    pass

                gw.sg.amplitude = 1.0
                print(gw.multimeter.voltage)

    """

    def __init__(
        self,
        addr: str = 'localhost',
        port: int = INSERV_DEFAULT_PORT,
        conn_timeout: float = 0.0,
        sync_timeout: float = RPYC_SYNC_TIMEOUT,
    ):
        """Initialize with the address and port of the InstrumentServer.

        Args:
            addr: Network address of the Instrument Server.
            port: Port number of the Instrument Server.
            conn_timeout: Lower bound on the time to wait for the connection to be established.
            sync_timeout: Time to wait for requests / function calls to finish
        Raises:
            InstrumentGatewayError: Connection to the InstrumentServer failed.
        """
        self.addr = addr
        self.port = port
        self.conn_timeout = conn_timeout
        self.sync_timeout = sync_timeout
        self._connection = None
        self._thread = None

    def connect(self):
        """Attempt connection to an InstrumentServer.

        Raises:
            InstrumentGatewayError: Connection to the InstrumentServer failed.
        """
        timeout = time.time() + self.conn_timeout
        while True:
            try:
                # connect to the rpyc server running on the instrument server
                self._connection = rpyc.connect(
                    self.addr,
                    self.port,
                    config={
                        'allow_pickle': True,
                        'timeout': RPYC_CONN_TIMEOUT,
                        'sync_request_timeout': self.sync_timeout,
                    },
                )
                # start up a background thread to fullfill requests on the client side
                # TODO - not sure if we want a background thread or not
                # self._thread = rpyc.BgServingThread(self._connection)

                # this allows the instrument server to have full access to this client's object dictionaries - appears necessary for lantz
                self._connection._config['allow_all_attrs'] = True
            except OSError as exc:
                logger.debug(
                    f'Gateway couldn\'t connect to instrument server at "{self.addr}:{self.port}"- retrying...'
                )
                if time.time() > timeout:
                    raise InstrumentGatewayError(
                        f'Failed to connect to instrument server at "{self.addr}:{self.port}"'
                    ) from exc
                # rate limit retrying connection
                time.sleep(0.5)
            else:
                logger.info(
                    f'Gateway connected to instrument server at "{self.addr}:{self.port}"'
                )
                break

    def disconnect(self):
        """Disconnect from the instrument server."""
        # TODO - not sure if we want a background thread or not
        # self._thread.stop()
        self._thread = None
        self._connection.close()
        self._connection = None
        logger.info(f'Gateway disconnected from server at {self.addr}:{self.port}')

    def reconnect(self):
        """Disconnect then connect to the instrument server

        Raises:
            InstrumentGatewayError: Connection to the InstrumentServer failed.
        """
        self.disconnect()
        self.connect()

    def __getattr__(self, attr: str):
        """Allow the user to access the server objects directly using gateway.device notation, e.g. gateway.sg.amplitude"""
        if self._connection:
            try:
                return getattr(self._connection.root, attr)
            except EOFError:
                # the server might have disconnected - try reconnecting
                self.reconnect()
                return getattr(self._connection.root, attr)
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)

    def __enter__(self):
        """Python context manager setup"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.disconnect()
