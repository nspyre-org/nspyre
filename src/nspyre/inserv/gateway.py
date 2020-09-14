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

from pint import Quantity
import parse
import pymongo

import rpyc

# nspyre
from nspyre.config.config_files import get_config_param, load_config
from nspyre.utils.misc import MonkeyWrapper
from nspyre.definitions import CLIENT_META_CONFIG_PATH, MONGO_CONNECT_TIMEOUT, \
                                MONGO_SERVERS_KEY, MONGO_SERVERS_SETTINGS_KEY, \
                                MONGO_RS, RPYC_CONN_TIMEOUT, INSERV_DEV_ACCESSOR
from nspyre.definitions import Q_

###########################
# globals
###########################

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

class InservGateway():
    """Loads a configuration file, then attempts to connect to all 
    instrument servers"""
    def __init__(self, config_file=CLIENT_META_CONFIG_PATH, mongo_addr=None):
        # config dictionary
        self.config = {}
        # list of available instrument servers fetched from mongo
        self.servers = {}
        self.mongo_addr = None
        self.mongo_client = None
        self.update_config(config_file)
        self.config_mongo(mongo_addr)
        self.connect_servers()
        # a dictionary containing all available devices on the
        # instrument servers
        # the syntax for keys in the devs dictionary is
        # '<inserv name>/<inserv device name>' e.g. 'server1/dev1'
        self.devs = self.load_devices()

    def config_mongo(self, mongo_addr=None):
        """Set up the mongodb database (but connection won't take place until
        a query is made)"""
        if mongo_addr:
            self.mongo_addr = mongo_addr
        else:
            self.mongo_addr,_ = get_config_param(self.config, ['mongodb_addr'])
        logging.info('connecting to mongodb server [{}]...'.\
                            format(self.mongo_addr))
        self.mongo_client = pymongo.MongoClient(mongo_addr,
                            replicaset=MONGO_RS,
                            serverSelectionTimeoutMS=MONGO_CONNECT_TIMEOUT)

    def connect_servers(self):
        """Auto discover and attempt connection to all of the instrument
        servers in mongodb"""
        # retrieve all of the instrument server settings from mongo
        try:
            all_db_names = self.mongo_client.list_database_names()
        except:
            raise InservGatewayError('Failed connecting to mongodb [{}]'.\
                                        format(self.mongo_addr)) from None
        logging.info('connected to mongodb server [{}]'.format(self.mongo_addr))
        for db_name in all_db_names:
            server_name = parse.parse(MONGO_SERVERS_KEY, db_name)
            # filter out all of the dbs that aren't instrument servers
            if server_name:
                # if the name was extracted successfully,
                # get it's value as a string
                server_name = server_name[0]
                # retrieve the server settings dictionary
                db_entry = self.mongo_client[db_name]\
                                    [MONGO_SERVERS_SETTINGS_KEY].find_one()
                self.connect_server(server_name,
                                    db_entry['address'],
                                    db_entry['port'])

    def disconnect_servers(self):
        """Attempt disconnection from all of the instrument servers"""
        for s in list(self.servers):
            self.disconnect_server(s)

    def connect_server(self, s_id, s_addr, s_port):
        """Attempt connection to an instrument server"""
        try:
            self.servers[s_id] = rpyc.connect(s_addr, s_port,
                                        config={'timeout' : RPYC_CONN_TIMEOUT})
            # this allows the instrument server to have full access to this
            # client's object dictionaries - appears necessary for lantz
            self.servers[s_id]._config['allow_all_attrs'] = True
        except:
            raise InservGatewayError('Failed to connect to '
                            'instrument server [{}] at address [{}]'.\
                            format(s_id, s_addr)) from None
        logging.info('instrument server gateway connected to instrument '
                    'server [{}]'.format(s_id))

    def disconnect_server(self, s_id):
        """Disconnect from an instrument server and remove it's associated 
        devices"""
        try:
            self.servers[s_id].close()
            del self.servers[s_id]
        except:
            raise InservGatewayError('Failed to disconnect from '
                            'instrument server [{}]'.format(s_id)) from None
        logging.info('instrument server gateway disconnected '
                        'from server [{}]'.format(s_id))

    def load_devices(self):
        """Iterate through the devices in the instrument servers, and return a
        monkey-wrapped version of them (to solve pint unit registry issues)"""
        devs = {}
        for server_name in self.servers:
            # see inserv.py and RPyC documentation for how
            # the device is retrieved from the instrument server
            for dev_name in self.servers[server_name].root.devs:
                # pint has an associated unit registry, and Quantity objects
                # cannot be shared between registries. Because Quantity objects
                # coming from the instrument server have a different unit
                # registry they must be converted to Quantity objects of the
                # local registry.
                # see pint documentation for details
                def dev_get_attr(obj, attr):
                    ret = getattr(obj, attr)
                    if isinstance(ret, Quantity):
                        try:
                            quantity_ret = Q_(ret.m, str(ret.u))
                        except:
                            raise InservGatewayError('Instrument server '
                                '[{}] device [{}] attribute [{}] returned a '
                                'unit not found in the pint unit registry'.\
                                format(server_name, dev_name, attr))
                        return quantity_ret
                    else:
                        return ret
                # monkey wrap the device so we can override it's getter
                # to fix pint unit registry issue
                devs[INSERV_DEV_ACCESSOR.format(server_name, dev_name)] = \
                MonkeyWrapper(self.servers[server_name].root.devs[dev_name],
                                get_attr_override=dev_get_attr)
                logging.info('instrument server gateway loaded device [{}] '
                            'from server [{}]'.format(dev_name, server_name))
        return devs

    def update_config(self, filename):
        """Reload the config file"""
        self.config = load_config(filename)

    def __enter__(self):
        """Python context manager setup"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.disconnect_servers()

if __name__ == '__main__':
    # configure server logging behavior
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s -- %(levelname)s -- %(message)s',
                        handlers=[logging.StreamHandler()])
    # TODO unit testing module
    with InservGateway() as im:
        sg_loc = 'local1/fake_sg'
        im.devs[sg_loc].amplitude = Q_(1.0, 'volt')
        print('found devices:\n{}'.format(im.devs))
        print(Q_(5, 'volt') + im.devs[sg_loc].amplitude)
