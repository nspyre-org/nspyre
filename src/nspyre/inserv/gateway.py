"""
This module manages and centralizes connections to one or more instrument
servers. All instrument server connections should be done through the
InservGateway class.

Author: Jacob Feder
Date: 7/11/2020
"""

###########################
# imports
###########################

# std
import os
import logging

# 3rd party
import parse
import rpyc

# nspyre
from nspyre.misc.misc import register_quantity_brining
from nspyre.config.config_files import get_config_param, load_config
from nspyre.definitions import RPYC_CONN_TIMEOUT, RPYC_SYNC_TIMEOUT, \
                            INSERV_DEV_ACCESSOR, CLIENT_META_CONFIG_PATH
from nspyre.definitions import Q_

# for properly serializing/deserializing quantity objects using the local
# pint unit registry
register_quantity_brining(Q_)

###########################
# globals
###########################

logger = logging.getLogger(__name__)

CONFIG_GATEWAY_SETTINGS = 'instrument_servers'
CONFIG_GATEWAY_DEVICES = 'devices'

###########################
# exceptions
###########################

class InservGatewayError(Exception):
    """General InservGateway exception"""
    def __init__(self, msg):
        super().__init__(msg)

###########################
# classes / functions
###########################

# Temporary monkey patching of rpyc to implement synchronous about_to_disconnect feature
# Need to define consts.HANDLE_ABOUT_TO_CLOSE before consts is import by protocol (this is done
# in the load of nspyre.inser.inserv)
import nspyre.inserv.inserv
from rpyc.core.protocol import consts

# Need to monkey patch VoidService for rpyc.utils.factory.connect_stream
from rpyc.core.service import Service
Service._protocol = nspyre.inserv.inserv.InstrumentConnection
Service = nspyre.inserv.inserv.InstrumentService
from rpyc.core.service import VoidService
VoidService = nspyre.inserv.inserv.VoidInstrumentService


class InservGateway():
    """Loads a configuration file, then attempts to connect to all 
    instrument servers

    This class is a representation of the instrument server from the
    client's perspective. It contains server connection information, and an
    instance variable object for each device connected to the remote instrument
    server
    """
    def __init__(self, config_file=None):
        # if the config file isn't specified, get it from the meta-config
        if not config_file:
            config_file = load_meta_config(CLIENT_META_CONFIG_PATH)
        # config dictionary
        self.config = {}
        # dictionary of available rpyc instrument servers
        # key is the server string id, value is a tuple (rpyc conn, bg thread)
        # e.g. {'local1': (rpyc.core.protocol.Connection, 
        #                  rpyc.utils.helpers.BgServingThread),
        #       'remote1': ...}
        self._servers = {}
        self.config = None
        self.reload_config(config_file)
        self.reconnect_servers()

    def reconnect_servers(self):
        """Attempt connection to all of the instrument servers specified in the config"""
        servers,_ = get_config_param(self.config, [CONFIG_GATEWAY_SETTINGS])
        # iterate through servers
        for server_name in servers:
            # only try connecting if there isn't already a connection
            if server_name not in self._servers:
                ip,_ = get_config_param(self.config, [CONFIG_GATEWAY_SETTINGS, server_name, 'ip'])
                port,_ = get_config_param(self.config, [CONFIG_GATEWAY_SETTINGS, server_name, 'port'])
                try:
                    self.connect_server(server_name, ip, port)
                except InservGatewayError:
                    logger.error('Couldn\'t connect to instrument server [{}]'.format(server_name))

    def disconnect_servers(self):
        """Attempt disconnection from all of the instrument servers"""
        for s in list(self._servers):
            self.disconnect_server(s)

    def connect_server(self, s_id, s_addr, s_port):
        """Attempt connection to an instrument server"""
        try:
            # connect to the rpyc server running on the instrument server
            # and start up a background thread to fullfill requests on the
            # client side
            conn = rpyc.connect(s_addr, s_port,
                            config={'allow_pickle' : True,
                                    'timeout' : RPYC_CONN_TIMEOUT,
                                    'sync_request_timeout': RPYC_SYNC_TIMEOUT})

            bg_serving_thread = rpyc.BgServingThread(conn)
            
            # this allows the instrument server to have full access to this
            # client's object dictionaries - appears necessary for lantz
            conn._config['allow_all_attrs'] = True

            self._servers[s_id] = (conn, bg_serving_thread)
        except BaseException:
            raise InservGatewayError('Failed to connect to '
                            'instrument server [{}] at address [{}]'.\
                            format(s_id, s_addr)) from None
        logger.info('instrument server gateway connected to instrument '
                    'server [{}]'.format(s_id))

    def disconnect_server(self, s_id):
        """Disconnect from an instrument server and remove it's associated 
        devices"""
        try:
            conn = self._servers[s_id][0]
            bg_serving_thread = self._servers[s_id][1]
            bg_serving_thread.stop()
            conn.close()
            del self._servers[s_id]
        except BaseException:
            raise InservGatewayError('Failed to disconnect from '
                            'instrument server [{}]'.format(s_id)) from None
        logger.info('instrument server gateway disconnected '
                        'from server [{}]'.format(s_id))

    def servers(self):
        """Return a dictionary containing 'server name' mapped to
        an rpyc conn object"""
        servers_dict = {}
        for s in self._servers:
            servers_dict[s] = self._servers[s][0]

        return servers_dict

    def __getattr__(self, attr):
        """Allow the user to access the server objects directly using
        e.g. gateway.server1.sig_gen.frequency notation"""
        if attr in self._servers:
            return self._servers[attr][0].root
        else:
            raise AttributeError('\'{}\' object has no attribute \'{}\''.\
                        format(self.__class__.__name__, attr))

    def reload_config(self, filename):
        """Reload the config file"""
        self.config = load_config(filename)

    def __enter__(self):
        """Python context manager setup"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.disconnect_servers()
