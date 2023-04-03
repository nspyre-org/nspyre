"""
This module provides an interface to control devices on an :py:class:`~nspyre.instrument.server.InstrumentServer`.
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
from .server import INSTRUMENT_SERVER_DEFAULT_PORT
from .server import RPYC_SYNC_TIMEOUT

_logger = logging.getLogger(__name__)

RPYC_CONN_TIMEOUT = 30
"""RPyC connection timeout in seconds (None for no timeout)."""


class InstrumentGatewayError(Exception):
    """Raised for failures related to the :py:class:`~nspyre.instrument.server.InstrumentServer`."""


class InstrumentGateway:
    """Create a connection to an :py:class:`~nspyre.instrument.server.InstrumentServer` and access it's devices."""

    def __init__(
        self,
        addr: str = 'localhost',
        port: int = INSTRUMENT_SERVER_DEFAULT_PORT,
        conn_timeout: float = 0.0,
        sync_timeout: float = RPYC_SYNC_TIMEOUT,
    ):
        """
        Args:
            addr: Network address of the :py:class:`~nspyre.instrument.server.InstrumentServer`.
            port: Port number of the :py:class:`~nspyre.instrument.server.InstrumentServer`.
            conn_timeout: Lower bound on the time to wait for the connection to be established.
            sync_timeout: Time to wait for requests / function calls to finish

        Raises:
            InstrumentGatewayError: Connection to the :py:class:`~nspyre.instrument.server.InstrumentServer` failed.
        """
        self.addr = addr
        self.port = port
        self.conn_timeout = conn_timeout
        self.sync_timeout = sync_timeout
        self._connection = None
        self._thread = None

    def connect(self):
        """Attempt connection to an :py:class:`~nspyre.instrument.server.InstrumentServer`.

        Raises:
            InstrumentGatewayError: Connection to the :py:class:`~nspyre.instrument.server.InstrumentServer` failed.
        """
        timeout = time.time() + self.conn_timeout
        while True:
            try:
                # connect to the instrument server rpyc server
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
                _logger.debug(
                    f'Gateway couldn\'t connect to instrument server at "{self.addr}:{self.port}"- retrying...'
                )
                if time.time() > timeout:
                    raise InstrumentGatewayError(
                        f'Failed to connect to instrument server at "{self.addr}:{self.port}"'
                    ) from exc
                # rate limit retrying connection
                time.sleep(0.5)
            else:
                _logger.info(
                    f'Gateway connected to instrument server at "{self.addr}:{self.port}"'
                )
                break

    def disconnect(self):
        """Disconnect from the :py:class:`~nspyre.instrument.server.InstrumentServer`."""
        # TODO - not sure if we want a background thread or not
        # self._thread.stop()
        self._thread = None
        self._connection.close()
        self._connection = None
        _logger.info(f'Gateway disconnected from server at {self.addr}:{self.port}')

    def reconnect(self):
        """Disconnect then connect to the :py:class:`~nspyre.instrument.server.InstrumentServer` again.

        Raises:
            InstrumentGatewayError: Connection to the :py:class:`~nspyre.instrument.server.InstrumentServer` failed.
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
