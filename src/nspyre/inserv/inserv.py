"""
This module:
    - loads the server config file
    - connects to all of the instruments specified in the config files
    - creates a RPyC (python remote procedure call) server to allow remote
        machines to access the instruments (should be done using InservGateway)

Author: Jacob Feder
Date: 7/8/2020
"""

###########################
# imports
###########################

# std
from pathlib import Path
import logging
import threading
import time
from functools import partial
import copy

# 3rd party
import rpyc
from rpyc.utils.server import ThreadedServer 
import pymongo
from lantz import Q_, DictFeat
from pint import Quantity

# nspyre
from nspyre.utils.misc import register_quantity_brining
from nspyre.config.config_files import get_config_param, load_config, \
                                    meta_config_add, meta_config_remove, \
                                    meta_config_files, ConfigEntryNotFoundError
from nspyre.utils.misc import load_class_from_str, load_class_from_file
from nspyre.definitions import MONGO_SERVERS_KEY, \
                MONGO_SERVERS_SETTINGS_KEY, MONGO_CONNECT_TIMEOUT, \
                MONGO_RS, RPYC_SYNC_TIMEOUT, CONFIG_MONGO_ADDR_KEY, \
                join_nspyre_path

# for properly serializing/deserializing quantity objects using the local
# pint unit registry
register_quantity_brining(Q_)

###########################
# globals
###########################

CONFIG_SERVER_SETTINGS = 'server_settings'
CONFIG_SERVER_DEVICES = 'devices'
CONFIG_SERVER_DEVICE_LANTZ_CLASS = 'lantz_class'
CONFIG_SERVER_DEVICE_CLASS_FILE = 'class_file'
CONFIG_SERVER_DEVICE_CLASS_NAME = 'class'

RPYC_SERVER_STOP_EVENT = threading.Event()

def test(key, value, old_value):
    print('{}: {} -> {}'.format(key, old_value, value))
    # print('{}[{}]: {} -> {}'.format(attr, key, old_value, value))
    # if isinstance(value, Quantity):
    #     value = value.to(self.devs[dev_name].\
    #                         _lantz_feats[attr]._kwargs['units']).m

###########################
# exceptions
###########################

class InstrumentServerError(Exception):
    """General InstrumentServer exception"""
    def __init__(self, error, msg):
        super().__init__(msg)
        if error:
            logging.exception(error)

###########################
# classes
###########################

class InstrumentServer(rpyc.Service):
    """RPyC provider that loads lantz devices and exposes them to the remote
    client"""
    def __init__(self, config_file, mongo_addr=None):
        super().__init__()
        # configuration
        self.config = {}
        self.config_file = None
        self.name = None
        # server settings
        self.ip = None
        self.port = None
        # rpyc server object
        self._rpyc_server = None
        # mongodb
        self.db_name = None
        self.mongo_addr = None
        self.mongo_client = None
        self.db = None
        # lantz devices
        self.devs = {}

        # storage container for hook methods that update mongodb feats when
        # lantz feats are changed - this is required because pysignal uses
        # weakrefs, so any local functions you pass to it will fail when they
        # go out of scope
        self.feat_hook_functions = {}
        self.dictfeat_hook_functions = {}

        self.update_config(config_file)
        self.reload_server_config()
        self.start_server()
        self.reload_devices()

    def restart(self, config_file=None, mongo_addr=None):
        """Restart the server AND reload the config file and all devices"""
        logging.info('restarting...')
        self.update_config(config_file)
        self.reload_server_config()
        self.reload_devices()
        self.reload_server()

    def reload_server_config(self):
        """Reload RPyC server settings from the config"""
        self.name,_ = get_config_param(self.config, \
                        [CONFIG_SERVER_SETTINGS, 'name'])
        self.ip,_ = get_config_param(self.config, \
                        [CONFIG_SERVER_SETTINGS, 'ip'])
        self.port,_ = get_config_param(self.config, \
                        [CONFIG_SERVER_SETTINGS, 'port'])

    def connect_mongo(self, mongo_addr=None):
        """Config and connect to the mongodb database"""
        self.db_name = MONGO_SERVERS_KEY.format(self.name)
        if mongo_addr:
            self.mongo_addr = mongo_addr
        else:
            self.mongo_addr,_ = get_config_param(self.config, \
                                                [CONFIG_MONGO_ADDR_KEY])
        logging.info('connecting to mongodb server [{}]...'.\
                        format(self.mongo_addr))
        self.mongo_client = pymongo.MongoClient(mongo_addr,
                            replicaset=MONGO_RS,
                            serverSelectionTimeoutMS=MONGO_CONNECT_TIMEOUT)
        self.db = self.mongo_client[self.db_name]
        # mongodb doesn't do any actual database queries until you try to
        # perform an action on the database, so this is the point where
        # connection will occur
        try:
            current_db = self.mongo_client[self.db_name]\
                                    [MONGO_SERVERS_SETTINGS_KEY].find_one()
        except Exception as exc:
            raise InstrumentServerError(exc, 'Failed connecting to mongodb '
                                    '[{}]'.format(self.mongo_addr)) from None
        try:
            current_db_address = current_db['address']
        except:
            current_db_address = self.ip
        # check that there isn't already an instrument server with same
        # name but different address
        if current_db_address != self.ip:
            raise InstrumentServerError('An instrument server with the name '
                    '[{}] and a different address [{}] is already present on '
                    'mongodb. Instrument servers must have unique names.'.\
                    format(self.name, current_db_address)) from None
        self.mongo_client.drop_database(self.db_name)
        # add a special settings document so clients can auto-detect us
        self.db[MONGO_SERVERS_SETTINGS_KEY].insert_one({'address' : self.ip,
                                                    'port' : self.port})
        logging.info('connected to mongodb server [{}]'.format(self.mongo_addr))

    def disconnect_mongo(self):
        """Disconnect from the mongodb database"""
        # remove the database entry from mongo
        self.mongo_client.drop_database(self.db_name)
        # disconnect
        self.mongo_client.close()

    def add_device(self, dev_name):
        """Add and initialize a device"""

        # load the device parameters from the config file
        
        # first try getting the driver's lantz class
        try:
            dev_lantz_class, dev_class_cfg_file = get_config_param(self.config,
                                        [CONFIG_SERVER_DEVICES, dev_name, \
                                        CONFIG_SERVER_DEVICE_LANTZ_CLASS])
            try:
                dev_class = load_class_from_str('lantz.drivers.' + \
                                                dev_lantz_class)
            except Exception as exc:
                raise InstrumentServerError(exc, 'The specified lantz driver '
                    '[{}] for device [{}] couldn\'t be loaded'.\
                    format(dev_lantz_class, dev_name))
        except ConfigEntryNotFoundError:
            # if the lantz class isn't defined, try getting an absolute file
            # path and class name
            try:
                dev_class_file_str, dev_class_file_cfg_file = \
                                    get_config_param(self.config,
                                            [CONFIG_SERVER_DEVICES, dev_name, 
                                            CONFIG_SERVER_DEVICE_CLASS_FILE])
                dev_class_name,_ = get_config_param(self.config,
                                            [CONFIG_SERVER_DEVICES, dev_name, 
                                            CONFIG_SERVER_DEVICE_CLASS_NAME])
            except ConfigEntryNotFoundError as exc:
                raise InstrumentServerError(exc, 'The device [{}] didn\'t '
                    'contain an entry for either a lantz class "{}" or a file '
                    'path "{}" / class name "{}" to define it\'s driver type'.\
                    format(dev_name, CONFIG_SERVER_DEVICE_LANTZ_CLASS, 
                            CONFIG_SERVER_DEVICE_CLASS_FILE, 
                            CONFIG_SERVER_DEVICE_CLASS_NAME))
            dev_class_path = Path(dev_class_file_str)
            # resolve relative paths
            if not dev_class_path.is_absolute():
                dev_class_path = (Path(dev_class_file_cfg_file).parent / \
                                    dev_class_path).resolve()
            try:
                dev_class = load_class_from_file(dev_class_path, dev_class_name)
            except Exception as exc:
                raise InstrumentServerError(exc, 'The specified class [{}] '
                    'from file [{}] for device [{}] couldn\'t be loaded'.\
                    format(dev_class_name, dev_class_path, dev_name))

        dev_args,_ = get_config_param(self.config,
                                    [CONFIG_SERVER_DEVICES, dev_name, 'args'])
        dev_kwargs,_ = get_config_param(self.config,
                                    [CONFIG_SERVER_DEVICES, dev_name, 'kwargs'])

        # get an instance of the device
        try:
            self.devs[dev_name] = dev_class(*dev_args, **dev_kwargs)
        except Exception as exc:
            raise InstrumentServerError(exc, 'Failed to get instance of device '
                                        '{} of class {}'.\
                                        format(dev_name, dev_class)) from None

        # collect all of the lantz feature attributes
        feat_attr_list = []
        for feat_name, feat in list(dev_class._lantz_feats.items()) + \
                            list(dev_class._lantz_dictfeats.items()):
            # add a custom hook for updating mongodb whenever the feat/dictfeat is written
            if isinstance(feat, DictFeat):
                def update_mongo_dictfeat(value, old_value, key, attr=feat_name):
                    print('{}[{}]: {} -> {}'.format(attr, key, old_value, value))
                    if isinstance(value, Quantity):
                        value = value.to(self.devs[dev_name].\
                                            _lantz_dictfeats[attr]._kwargs['units']).m
                    self.db[dev_name].update_one({'name' : attr},
                                {'$set' : {'value.{}'.format(key) : value}},
                                upsert=True)
                self.dictfeat_hook_functions[feat_name] = update_mongo_dictfeat
                getattr(self.devs[dev_name], feat_name + '_changed').connect(self.dictfeat_hook_functions[feat_name])
            else:
                def update_mongo_feat(value, old_value, attr=feat_name):
                    print('{}: {} -> {}'.format(attr, old_value, value))
                    if isinstance(value, Quantity):
                        value = value.to(self.devs[dev_name].\
                                            _lantz_feats[attr]._kwargs['units']).m
                    self.db[dev_name].update_one({'name' : attr},
                                {'$set' : {'value' : value}},
                                upsert=True)
                self.feat_hook_functions[feat_name] = update_mongo_feat
                getattr(self.devs[dev_name], feat_name + '_changed').connect(self.feat_hook_functions[feat_name])

            attrs = copy.deepcopy(feat.__dict__['_config'])
            if isinstance(feat, DictFeat) and 'keys' in feat.__dict__:
                attrs['keys'] = feat.__dict__['keys']

            if attrs['limits']:
                if len(attrs['limits']) == 1:
                    limits = [0, attrs['limits'][0]]
                else:
                    limits = attrs['limits']

            else:
                limits = None

            if attrs['values']:
                values = list(attrs['values'])
            else:
                values = None
            
            if 'keys' in attrs and attrs['keys']:
                keys = list(attrs['keys']).sort()
            else:
                keys = None

            if 'keys' in attrs and attrs['keys'] and isinstance(feat, DictFeat):
                value = [None] * len(attrs['keys'])
            else:
                value = None

            feat_attr_list.append({
                'name':     feat_name,
                'type':     'dictfeat' if isinstance(feat, DictFeat) \
                                            else 'feat',
                'readonly': feat.__dict__['fset'] is None,
                'units':    attrs['units'],
                'limits':   limits,
                'values':   values,
                'keys':     keys,
                'value':    value
            })

        for action_name, action in dev_class._lantz_actions.items():
            feat_attr_list.append({'name' : action_name, 'type' : 'action'})

        self.db[dev_name].drop()
        # add all of the lantz feature attributes to the database
        self.db[dev_name].insert_many(feat_attr_list)

        # initialize the device
        try:
            self.devs[dev_name].initialize()
        except Exception as exc:
            logging.error(exc)
            self.devs.pop(dev_name)
            logging.error('device [{}] initialization sequence failed'.\
                            format(dev_name))
            return

        logging.info('added device [{}] with args: {} kwargs: {}'.\
                        format(dev_name, dev_args, dev_kwargs))

    def del_device(self, dev_name):
        """Remove and finalize a device"""
        try:
            self.devs.pop(dev_name).finalize()
        except Exception as exc:
            raise InstrumentServerError(exc, 'Failed deleting device [{}]'.\
                                        format(dev_name)) from None
        logging.info('deleted [{}]'.format(dev_name))

    def reload_device(self, dev_name):
        """Remove a device, then reload it from the stored config"""
        if dev_name in self.devs:
            self.del_device(dev_name)
        self.add_device(dev_name)

    def reload_devices(self):
        """Reload all devices"""
        devs,_ = get_config_param(self.config, ['devices'])
        for dev_name in devs:
            self.reload_device(dev_name)
        logging.info('reloaded all devices')

    def update_config(self, config_file=None):
        """Reload the config files"""
        # update the config with a new file if one was passed as argument
        if config_file:
            self.config_file = config_file
        # reload the config dictionary
        self.config = load_config(self.config_file)
        logging.info('loaded config files {}'.\
                        format(list(self.config.keys())))

    def on_connect(self, conn):
        """Called when a client connects to the RPyC server"""
        logging.info('client [{}] connected'.format(conn))

    def on_disconnect(self, conn):
        """Called when a client discconnects from the RPyC server"""
        logging.info('client [{}] disconnected'.format(conn))

    def reload_server(self):
        """Restart the RPyC server"""
        self.stop_server()
        self.start_server()

    def start_server(self):
        """Start the RPyC server"""
        if self._rpyc_server:
            logging.warning('can\'t start the rpyc server because one '
                            'is already running')
            return
        self.connect_mongo()
        thread = threading.Thread(target=self._rpyc_server_thread)
        thread.start()
        # wait for the server to start
        while not (self._rpyc_server and self._rpyc_server.active):
            time.sleep(0.1)

    def stop_server(self):
        """Stop the RPyC server"""
        self.disconnect_mongo()
        if not self._rpyc_server:
            logging.warning('can\'t stop the rpyc server because there '
                            'isn\'t one running')
            return
        logging.info('stopping RPyC server...')
        self._rpyc_server.close()
        # wait for the server to stop
        while self._rpyc_server.active:
            time.sleep(0.1)
        RPYC_SERVER_STOP_EVENT.wait()
        RPYC_SERVER_STOP_EVENT.clear()
        self._rpyc_server = None

    def _rpyc_server_thread(self):
        """Thread for running the RPyC server asynchronously"""
        logging.info('starting RPyC server...')
        self._rpyc_server = ThreadedServer(self, port=self.port,
                        protocol_config={'allow_pickle' : True,
                                    'allow_all_attrs' : True,
                                    'allow_setattr' : True,
                                    'allow_delattr' : True,
                                    'sync_request_timeout' : RPYC_SYNC_TIMEOUT})
        self._rpyc_server.start()
        logging.info('RPyC server stopped')
        RPYC_SERVER_STOP_EVENT.set()
