#!/usr/bin/env python
"""
    nspyre.inserv.inserv.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    This module:
    - loads the server config file
    - connects to all of the instruments specified in the config files
    - creates a RPyC (python remote procedure call) server to allow remote
        machines to access the instruments
    - serves a shell prompt allowing the user runtime control of the server

    Author: Jacob Feder
    Date: 7/8/2020
"""

import logging
from nspyre.config.config_files import get_config_param, load_config, \
                                        meta_config_add, meta_config_remove, \
                                        meta_config_files
from nspyre.utils.misc import load_class_from_str, join_nspyre_path, \
                                MonkeyWrapper
from nspyre.definitions import SERVER_META_CONFIG_YAML, MONGO_SERVERS_KEY, \
                                MONGO_SERVERS_SETTINGS, MONGO_CONNECT_TIMEOUT, \
                                MONGO_RS
import rpyc
import os
import _thread
import pymongo
from cmd import Cmd
import time
from rpyc.utils.server import ThreadedServer 
import argparse
import waiting
from lantz import DictFeat, Q_
from pint import Quantity
import sys
import visa

###########################
# Globals
###########################

DEFAULT_LOG = 'server.log'
# in ms
RPYC_TIMEOUT = 5000

###########################
# Exceptions
###########################

class InstrumentServerError(Exception):
    """General InstrumentServer exception"""
    def __init__(self, error, msg):
        super().__init__(msg)
        if error:
            logging.exception(error)

###########################
# Classes
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
        self.name = get_config_param(self.config, ['server_settings', 'name'])
        self.ip = get_config_param(self.config, ['server_settings', 'ip'])
        self.port = get_config_param(self.config, ['server_settings', 'port'])
        
    def connect_mongo(self, mongo_addr=None):
        """Config and connect to the mongodb database"""
        self.db_name = MONGO_SERVERS_KEY.format(self.name)
        self.mongo_addr = mongo_addr if mongo_addr else \
                            get_config_param(self.config, ['mongodb_addr'])
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
                                    [MONGO_SERVERS_SETTINGS].find_one()
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
        self.db[MONGO_SERVERS_SETTINGS].insert_one({'address' : self.ip,
                                                    'port' : self.port})
        logging.info('connected to mongodb server [{}]'.format(self.mongo_addr))

    def disconnect_mongo(self):
        """Disconnect from the mongodb database"""
        # remove the database entry from mongo
        self.mongo_client.drop_database(self.db_name)
        # disconnect
        self.mongo_client.close()

    def add_device(self, dev_name, dev_class, dev_args, dev_kwargs):
        """Add and initialize a device"""

        # get the device lantz class
        try:
            dev_class = load_class_from_str(dev_class)
        except Exception as exc:
            raise InstrumentServerError(exc, 'Tried to initialize device [{}] '
                                        'with unrecognized class [{}]'.\
                                        format(dev_name, dev_class)) from None

        # a monkey-patching function for overriding writing devices feats
        def dev_set_attr(obj, attr, val):
            if isinstance(val, Quantity):
                # pint has an associated unit registry, and Quantity objects
                # cannot be shared between registries. Because Quantity objects
                # coming from the remote client have a different unit registry,
                # they must be converted to Quantity objects of the local lantz
                # registry (aka Q_ -> defined in lantz __init__.py).
                # see pint documentation for details
                try:
                    setattr(obj, attr, Q_(val.m, str(val.u)))
                except Exception as exc:
                    raise InstrumentServerError(exc, 'Remote client attempted '
                        'setting instrument server device [{}] attribute [{}] '
                        'to a unit not found in the pint unit registry'.\
                        format(obj, attr))
            else:
                setattr(obj, attr, val)
            # update the mongodb entry for this feat
            base_units = self.devs[dev_name]._lantz_feats[attr]._kwargs['units']
            formatted_val = val.to(base_units).m if isinstance(val, Quantity) \
                                                else val
            self.db[dev_name].update_one({'name':attr},
                                        {'$set':{'value':formatted_val}},
                                        upsert=True)

        # get an instance of the device
        try:
            self.devs[dev_name] = \
                    MonkeyWrapper(dev_class(*dev_args, **dev_kwargs),
                                    set_attr_override=dev_set_attr)
        except Exception as exc:
            raise InstrumentServerError(exc, 'Failed to get instance of device '
                                        '{} of class {}'.\
                                        format(dev_name, dev_class)) from None

        # collect all of the lantz feature attributes
        feat_attr_list = list()
        for feat_name, feat in dev_class._lantz_feats.items():
            attrs = feat.__dict__['_config']

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
                value = [None] * len(attrs['values'])
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
            logging.debug(exc)
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
        dev_params = get_config_param(self.config, ['devices', dev_name])
        dev_class = get_config_param(self.config,
                                    ['devices', dev_name, 'class'])
        dev_args = get_config_param(self.config,
                                    ['devices', dev_name, 'args'])
        dev_kwargs = get_config_param(self.config,
                                    ['devices', dev_name, 'kwargs'])
        self.add_device(dev_name, dev_class, dev_args, dev_kwargs)

    def reload_devices(self):
        """Reload all devices"""
        for dev_name in get_config_param(self.config, ['devices']):
            self.reload_device(dev_name)
        logging.info('reloaded all devices')

    def update_config(self, config_file=None):
        """Reload the config files"""
        # update the config with a new file if one was passed as argument
        if config_file:
            self.config_file = config_file
        # reload the config dictionary
        self.config, files = load_config(self.config_file)
        logging.info('loaded config files {}'.format(files))

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
        _thread.start_new_thread(self._rpyc_server_thread, ())
        # wait for the server to start
        waiting.wait(lambda: self._rpyc_server and self._rpyc_server.active,
                        sleep_seconds=0.1)

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
        waiting.wait(lambda: not self._rpyc_server.active, sleep_seconds=0.1)
        self._rpyc_server = None

    def _rpyc_server_thread(self):
        """Thread for running the RPyC server asynchronously"""
        logging.info('starting RPyC server...')
        self._rpyc_server = ThreadedServer(self, port=self.port,
                        protocol_config={'allow_all_attrs' : True,
                                        'allow_setattr' : True,
                                        'allow_delattr' : True,
                                        'sync_request_timeout' : RPYC_TIMEOUT})
        self._rpyc_server.start()
        logging.info('RPyC server stopped')

class InservCmdPrompt(Cmd):
    """Instrument Server shell prompt processor"""
    def __init__(self, inserv):
        super().__init__()
        self.inserv = inserv

    def emptyline(self):
        """When no command is entered"""
        pass

    def do_list(self, arg_string):
        """List all the available devices"""
        if arg_string:
            print('Expected 0 args')
            return
        for d in self.inserv.devs.keys():
            print(d)

    def do_config(self, arg_string):
        """Reload the server config files"""
        if arg_string:
            print('Expected 0 args')
            return
        # attempt to reload the config files
        try:
            self.inserv.update_config(config_file=\
                                    args[0] if arg_string else None)
        except Exception as exc:
            logging.exception(exc)
            print('Failed to reload config files')
            return

    def do_dev(self, arg_string):
        """Restart the connection with a device\n<string> the device name"""
        args = arg_string.split(' ')
        if not arg_string or len(args) > 1:
            print('Expected 1 arg: device name')
            return
        dev_name = args[0]
        try:
            self.inserv.reload_device(dev_name)
        except Exception as exc:
            logging.exception(exc)
            print('Failed to reload device [{}]'.format(dev_name))
            return

    def do_dev_all(self, arg_string):
        """Restart the connection with all devices"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            self.inserv.reload_devices()
        except Exception as exc:
            logging.exception(exc)
            print('Failed to reload all devices')
            return

    def do_restart(self, arg_string):
        """Restart the server AND reload the config file and all devices"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            self.inserv.restart()
        except Exception as exc:
            logging.exception(exc)
            print('Failed to restart')
            return

    def do_server_restart(self, arg_string):
        """Restart the rpyc server"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            self.inserv.reload_server()
        except Exception as exc:
            logging.exception(exc)
            print('Failed to restart server')
            return

    def do_server_stop(self, arg_string):
        """Stop the rpyc server"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            self.inserv.stop_server()
        except Exception as exc:
            logging.exception(exc)
            print('Failed to stop server')
            return

    def do_server_start(self, arg_string):
        """Start the rpyc server"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            self.inserv.start_server()
        except Exception as exc:
            logging.exception(exc)
            print('Failed to start server')
            return

    def do_debug(self, arg_string):
        """Drop into the debugging console"""
        if arg_string:
            print('Expected 0 args')
            return
        import pdb
        pdb.set_trace()

    def do_quit(self, arg_string):
        """Quit the program"""
        if arg_string:
            print('Expected 0 args')
            return
        logging.info('exiting...')
        # close all open resources
        self.inserv.stop_server()
        for dev_name in list(self.inserv.devs):
            self.inserv.del_device(dev_name)
        visa.ResourceManager().close()
        raise SystemExit

###########################
# standalone main
###########################

if __name__ == '__main__':
    # parse command-line arguments
    arg_parser = argparse.ArgumentParser(prog='inserv',
                            usage='%(prog)s [options]',
                            description='Run an nspyre instrument server')
    arg_parser.add_argument('-c', '--config', nargs='+',
                            default=None,
                            help='permanently add a configuration '
                            'file(s) to the list to be imported on startup')
    arg_parser.add_argument('-d', '--delconfig', nargs='+',
                            default=None,
                            help='remove a configuration file(s) from '
                            'the list to be imported on startup - pass either '
                            'the file path or its index')
    arg_parser.add_argument('-e', '--list_configs',
                            action='store_true',
                            help='list the configuration files to be '
                            'imported on startup')
    arg_parser.add_argument('-l', '--log',
                            default=DEFAULT_LOG,
                            help='log to the provided file location')
    arg_parser.add_argument('-m', '--mongo',
                            default=None,
                            help='use the provided mongodb address rather than '
                            'the one listed in the config (e.g. '
                            'mongodb://192.168.1.27:27017/)') 
    arg_parser.add_argument('-q', '--quiet',
                            action='store_true',
                            help='disable logging')
    arg_parser.add_argument('-v', '--verbosity',
                            default='info',
                            help='the verbosity of logging - options are: '
                            'debug, info, warning, error')
    cmd_args = arg_parser.parse_args()

    # configure server logging behavior
    if not cmd_args.quiet:
        if cmd_args.verbosity.lower() == 'debug':
            log_level = logging.DEBUG
        elif cmd_args.verbosity.lower() == 'info':
            log_level = logging.INFO
        elif cmd_args.verbosity.lower() == 'warning':
            log_level = logging.WARNING
        elif cmd_args.verbosity.lower() == 'error':
            log_level = logging.ERROR
        else:
            raise InstrumentServerError('didn\'t recognize logging level [{}]'.\
                                        format(cmd_args.verbosity)) from None

        logging.basicConfig(level=log_level,
                        format='%(asctime)s -- %(levelname)s -- %(message)s',
                        handlers=[logging.FileHandler(cmd_args.log, 'w+'),
                                logging.StreamHandler()])

    if cmd_args.config:
        # the user asked us to add config files to the meta-config
        meta_config_add(SERVER_META_CONFIG_YAML, cmd_args.config)
        sys.exit(0)
    if cmd_args.delconfig:
        # the user asked us to remove config files from the meta-config
        meta_config_remove(SERVER_META_CONFIG_YAML, cmd_args.delconfig)
        sys.exit(0)
    if cmd_args.list_configs:
        # the user asked us to list the config files from the meta-config
        files  = meta_config_files(SERVER_META_CONFIG_YAML)
        for i in range(len(files)):
            print('{}: {}'.format(i, files[i]))
        sys.exit(0)

    # init and start RPyC server
    logging.info('starting instrument server...')
    inserv = InstrumentServer(SERVER_META_CONFIG_YAML, cmd_args.mongo)

    # start the shell prompt event loop
    cmd_prompt = InservCmdPrompt(inserv)
    cmd_prompt.prompt = 'inserv > '
    cmd_prompt.cmdloop('instrument server started...')
