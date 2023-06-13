"""
This module provides an interface to control devices on an
:py:class:`~nspyre.instrument.server.InstrumentServer`.
"""
import logging
import time
from inspect import getmembers

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
from .server import InstrumentServer
from .server import InstrumentServerDeviceExistsError
from .server import InstrumentServerError

# add custom exceptions to rpyc cache
rpyc.core.vinegar._generic_exceptions_cache['nspyre.instrument.server.InstrumentServerDeviceExistsError'] = InstrumentServerDeviceExistsError
rpyc.core.vinegar._generic_exceptions_cache['nspyre.instrument.server.InstrumentServerError'] = InstrumentServerError

_logger = logging.getLogger(__name__)

RPYC_CONN_TIMEOUT = 30
"""RPyC connection timeout in seconds (None for no timeout)."""


def _members_list(cls) -> list:
    """Return a list of attributes for a provided class.

    Args:
        cls: The class to provide attributes for.

    Returns:
        A list of members.
    """
    member_tuples = getmembers(cls)
    members = []
    for m, _ in member_tuples:
        members.append(m)
    return members


_server_members = _members_list(InstrumentServer)


class InstrumentGatewayError(Exception):
    """Raised for failures related to the \
    :py:class:`~nspyre.instrument.gateway.InstrumentGateway`."""

    def __init__(self, *args, **kwargs):
        """
        Args:
            args: Arguments to pass to super class Exception().
            kwargs: Keyword arguments to pass to super class Exception().
        """
        # override this so that the docs don't the print superclass docstring
        super().__init__(*args, **kwargs)


class InstrumentGateway:
    """Create a connection to an \
    :py:class:`~nspyre.instrument.server.InstrumentServer` and access it's devices.
    When accessing a device through the gateway using :code:`gateway.my_device`
    notation, an :py:class:`InstrumentGatewayDevice` is returned.

    Usage Example:

    .. code-block:: python

        from nspyre import InstrumentGateway

        with InstrumentGateway() as gw:
            # d is an InstrumentGatewayDevice object
            d = gw.dev1
            # run the set_something() method of dev1
            d.set_something(5)
            # run the get_something() method of dev1 and print its return value
            print(d.get_something())
    """

    def __init__(
        self,
        addr: str = 'localhost',
        port: int = INSTRUMENT_SERVER_DEFAULT_PORT,
        conn_timeout: float = 0.0,
        sync_timeout: float = RPYC_SYNC_TIMEOUT,
    ):
        """
        Args:
            addr: Network address of the
                :py:class:`~nspyre.instrument.server.InstrumentServer`.
            port: Port number of the
                :py:class:`~nspyre.instrument.server.InstrumentServer`.
            conn_timeout: Lower bound on the time to wait for the connection to be
                established.
            sync_timeout: Time to wait for requests / function calls to finish.

        Raises:
            InstrumentGatewayError: Connection to the
                :py:class:`~nspyre.instrument.server.InstrumentServer` failed.
        """
        self.addr = addr
        self.port = port
        self.conn_timeout = conn_timeout
        self.sync_timeout = sync_timeout
        self._connection: rpyc.core.protocol.Connection = None
        self._thread = None

    def connect(self):
        """Attempt connection to an
        :py:class:`~nspyre.instrument.server.InstrumentServer`.

        Raises:
            InstrumentGatewayError: Connection to the
                :py:class:`~nspyre.instrument.server.InstrumentServer` failed.
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

                # this allows the instrument server to have full access to this
                # client's object dictionaries - appears necessary for lantz
                self._connection._config['allow_all_attrs'] = True
            except OSError as exc:
                _logger.debug(
                    'Gateway couldn\'t connect to instrument server at '
                    f'"{self.addr}:{self.port}"- retrying...'
                )
                if time.time() > timeout:
                    raise InstrumentGatewayError(
                        'Failed to connect to instrument server at '
                        f'"{self.addr}:{self.port}".'
                    ) from exc
                # rate limit retrying connection
                time.sleep(0.5)
            else:
                _logger.info(
                    'Gateway connected to instrument server at '
                    f'"{self.addr}:{self.port}".'
                )
                break

    def is_connected(self) -> bool:
        """Return whether the gateway is connected."""
        if self._connection is not None:
            return True
        else:
            return False

    def disconnect(self):
        """Disconnect from the
        :py:class:`~nspyre.instrument.server.InstrumentServer`."""
        # TODO - not sure if we want a background thread or not
        # self._thread.stop()
        # self._thread = None
        self._connection.close()
        self._connection = None
        _logger.info(f'Gateway disconnected from server at {self.addr}:{self.port}')

    def reconnect(self):
        """Disconnect then connect to the
        :py:class:`~nspyre.instrument.server.InstrumentServer` again.

        Raises:
            InstrumentGatewayError: Connection to the
                :py:class:`~nspyre.instrument.server.InstrumentServer` failed.
        """
        self.disconnect()
        self.connect()

    def __getattr__(self, attr: str):
        """Allow the user to access the server objects directly using gateway.device
        notation, e.g. gateway.sg.amplitude."""
        try:
            if self.is_connected():
                if attr in _server_members or attr[0] == '_':
                    # the user is trying to access an attribute of the instrument server
                    return getattr(self._connection.root, attr)
                else:
                    if hasattr(self._connection.root, attr):
                        # the user is trying to access a device - return a nice wrapper
                        # for the device
                        return InstrumentGatewayDevice(attr, self)
                    else:
                        # the device doesn't exist, so raise the default error
                        return getattr(self._connection.root, attr)
            else:
                raise EOFError
        except EOFError:
            # the server might have disconnected - try reconnecting
            if self.is_connected():
                self.reconnect()
            else:
                self.connect()
            return getattr(self._connection.root, attr)

    def __enter__(self):
        """Python context manager setup"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.disconnect()


class InstrumentGatewayDevice:
    def __init__(self, name: str, gateway: InstrumentGateway):
        """Wrapper for a device residing in an \
        :py:class:`~nspyre.instrument.gateway.InstrumentGateway`.
        When we access an attribute of a device from an
        :py:class:`~nspyre.instrument.gateway.InstrumentGateway`, it will
        return an rpyc netref object. This creates a problem when the gateway
        disconnects from the instrument server, then later reconnects. If we
        have an rpyc netref that pointed to a device attribute, it will be stale
        because it was linked to the original gateway. However, if we instead
        pass around this InstrumentGatewayDevice, we can always re-access the
        gateway device whenever we want to access an attribute of the device.
        This way, if the gateway disconnects then reconnects, we will always be
        accessing the attributes of the newly connected gateway, rather than a
        stale netref.

        Accessing the "device" attribute will return (an rpyc netref to) the
        device object. Attributes of the device can be accessed directly
        from this object. E.g.:

        .. code-block:: python

            from nspyre import InstrumentGateway

            with InstrumentGateway() as gw:
                # let's assume "dev1" was created on the instrument server as an
                # instance of "MyDriver"

                # d is an InstrumentGatewayDevice object
                d = gw.dev1
                # run the get_something() method of dev1 and print its return value
                print(d.get_something())
                # does the same thing
                print(d.device.get_something())

                print(isinstance(gw.dev1, MyDriver)) # False
                print(isinstance(gw.dev1, InstrumentGatewayDevice)) # True
                print(isinstance(gw.dev1.device, MyDriver)) # True

        Args:
            name: Name of the device on the gateway.
            gateway: :py:class:`~nspyre.instrument.gateway.InstrumentGateway` object
                containing the device.
        """
        self.____gateway_dev_name__ = name
        self.____gateway__ = gateway

    def __getattr__(self, attr: str):
        if attr == 'device':
            return getattr(
                self.____gateway__._connection.root, self.____gateway_dev_name__
            )
        else:
            # Always re-access the gateway instance in case the gateway reconnected.

            return getattr(
                getattr(
                    self.____gateway__._connection.root, self.____gateway_dev_name__
                ),
                attr,
            )
