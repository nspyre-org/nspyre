"""
This module allows interfacing with an instrument server.

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""

import logging

import rpyc

from .inserv import INSERV_DEFAULT_PORT, RPYC_SYNC_TIMEOUT
from ..misc.pint import register_quantity_brining, Q_

# monkey-patch fix for pint module
register_quantity_brining(Q_)

logger = logging.getLogger(__name__)

# rpyc connection timeout in s
RPYC_CONN_TIMEOUT = None


class InstrumentGatewayError(Exception):
    """Raised for failures related to the Instrument Gateway."""


class InstrumentGateway:
    """This class is a wrapper around an RPyC server connection"""

    def __init__(self, addr: str = 'localhost', port: int = INSERV_DEFAULT_PORT):
        """Initialize a connection to an Instrument Server
        :param addr: network address of the Instrument Server
        :param port: port number of the Instrument Server
        """
        self.addr = addr
        self.port = port
        self._connection = None
        self._thread = None
        self.connect()

    def connect(self):
        """Attempt connection to an instrument server"""
        try:
            # connect to the rpyc server running on the instrument server
            self._connection = rpyc.connect(
                self.addr,
                self.port,
                config={
                    'allow_pickle': True,
                    'timeout': RPYC_CONN_TIMEOUT,
                    'sync_request_timeout': RPYC_SYNC_TIMEOUT,
                },
            )
            # start up a background thread to fullfill requests on the
            # client side
            self._thread = rpyc.BgServingThread(self._connection)

            # this allows the instrument server to have full access to this
            # client's object dictionaries - appears necessary for lantz
            self._connection._config['allow_all_attrs'] = True
        except Exception as exc:
            raise InstrumentGatewayError(
                f'Failed to connect to instrument server at "{self.addr}:{self.port}"'
            ) from exc
        logger.info(
            f'Gateway connected to instrument server at "{self.addr}:{self.port}"'
        )

    def disconnect(self):
        """Disconnect from the instrument server"""
        self._thread.stop()
        self._thread = None
        self._connection.close()
        self._connection = None
        logger.info(f'Gateway disconnected from server at {self.addr}:{self.port}')

    def reconnect(self):
        """Disconnect then connect to the instrument server"""
        self.disconnect()
        self.connect()

    def __getattr__(self, attr: str):
        """Allow the user to access the server objects directly using gateway.device notation
        e.g. gateway.sg.amplitude"""
        if self._connection:
            return getattr(self._connection.root, attr)
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)

    def __enter__(self):
        """Python context manager setup"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.disconnect()
