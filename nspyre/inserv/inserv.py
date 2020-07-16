#!/usr/bin/env python
"""
    nspyre.inserv.inserv.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    This module loads the server config file, connects to all of the specified
    instruments, then creates a RPyC (python remote procedure call) server to
    allow remote machines to access the instruments.

    Author: Jacob Feder
    Date: 7/8/2020
"""

import logging
from nspyre.utils.config_file import get_config_param, load_config, \
                                    get_class_from_str
from nspyre.utils.utils import monkey_wrap
import rpyc
import os
import _thread
import pymongo
from cmd import Cmd
import time
from rpyc.utils.server import ThreadedServer 
import argparse

###########################
# Globals
###########################

DEFAULT_CONFIG = 'config.yaml'
DEFAULT_LOG = 'server.log'

this_dir = os.path.dirname(os.path.realpath(__file__))

###########################
# Exceptions
###########################

class InstrumentServerError(Exception):
    """General InstrumentServer exception"""
    def __init__(self, msg):
        super().__init__(msg)

###########################
# Classes / functions
###########################

class InstrumentServer(rpyc.Service):
    """RPyC provider that loads lantz devices and exposes them to the remote
    client"""
    def __init__(self, config_file=None, mongodb_addr=None):
        super().__init__()
        # configuration
        self.config = {}
        self.config_file = None
        self.name = None
        # rpyc server settings
        self.port = None
        # rpyc server object
        self._rpyc_server = None
        # mongodb
        self.db_name = None
        self.db_addr = None
        self.db_client = None
        self.db = None
        # lantz devices
        self.devs = {}

        self.update_config(config_file)
        self.reload_server_config()
        self.reload_mongo(mongodb_addr)
        self.reload_devices()
        self.start_server()

    def restart(self, config_file=None, mongodb_addr=None):
        logging.info('restarting...')
        self.update_config(config_file)
        self.reload_server_config()
        self.reload_mongo(mongodb_addr)
        self.reload_devices()
        self.reload_server()

    def reload_server_config(self):
        """Reload RPyC server settings from the config"""
        self.name = get_config_param(self.config, ['server_settings', 'name'])
        self.port = get_config_param(self.config, ['server_settings', 'port'])
        
    def reload_mongo(self, mongodb_addr=None):
        """Config and connect to mongodb database"""
        self.db_name = 'Instrument_Server[%s]' % (self.name)
        self.db_addr = mongodb_addr if mongodb_addr else \
                            get_config_param(self.config, ['mongodb_addr'])
        logging.info('connecting to mongodb server [%s]...', self.db_addr)
        # TODO disconnect first?, timeout
        self.db_client = pymongo.MongoClient(mongodb_addr,
                                            replicaset='NSpyreSet')
        self.db = self.db_client[self.db_name]
        try:
            self.db_client.drop_database(self.db_name)
        except:
            raise InstrumentServerError('Failed connecting to mongodb [%s]' \
                                        % (self.db_addr)) from None
        logging.info('connected to mongodb server [%s]', self.db_addr)

    def add_device(self, dev_name, dev_class, dev_args, dev_kwargs):
        """Add and initialize a device"""

        # get the device lantz class
        try:
            dev_class = get_class_from_str(dev_class)
        except:
            raise InstrumentServerError('Tried to initialize device [%s] ' \
                                        'with unrecognized class [%s]'
                                        % (dev_name, dev_class)) from None

        # get an instance of the device
        try:
            self.devs[dev_name] = \
                    dev_class(*dev_args, **dev_kwargs)
        except:
            raise InstrumentServerError('Failed to get instance of device ' \
                                        '[%s] of class [%s]'
                                        % (dev_name, dev_class)) from None

        # method for overriding lantz feature getter/setters
        # see monkey_wrap() for more info
        # TODO
        import lantz
        lantz.core.feat.Feat.__get__ = \
                monkey_wrap(lantz.core.feat.Feat.__get__,
                                lambda a,k: print('args: %s kwargs: %s' % (a,k)),
                                None)
        lantz.core.feat.DictFeat.__get__ = \
                monkey_wrap(lantz.core.feat.DictFeat.__get__,
                                lambda a,k: print('args: %s kwargs: %s' % (a,k)),
                                None)

        # initialize it
        try:
            self.devs[dev_name].initialize()
        except:
            raise InstrumentServerError('Device [%s] initialization sequence ' \
                                        'failed' % (dev_name)) from None

        logging.info('added device %s [%a] [%a]' % (dev_name,
                                                    dev_args, dev_kwargs))

    def del_device(self, dev_name):
        """Remove and finalize a device"""
        try:
            self.devs.pop(dev_name).finalize()
        except:
            raise InstrumentServerError('Failed deleting device [%s]' \
                                        % (dev_name)) from None
        logging.info('deleted %s' % (dev_name))

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
        """Reload the config file"""
        # update the config file if a new one was passed as argument
        if config_file:
            self.config_file = config_file
        self.config = load_config(self.config_file)
        logging.info('loaded config file [%s]' % (self.config_file))

    def on_connect(self, conn):
        """Called when a client connects to the RPyC server"""
        # TODO print client address
        logging.info('client [%s] connected' % (conn))

    def on_disconnect(self, conn):
        """Called when a client discconnects from the RPyC server"""
        # TODO print client address
        logging.info('client [%s] disconnected' % (conn))

    def reload_server(self):
        """Restart the RPyC server"""
        self.stop_server()
        self.start_server()

    def start_server(self):
        """Start the RPyC server"""
        if self._rpyc_server:
            logging.warning('can\'t start the rpyc server because one ' \
                            'is already running')
            return
        _thread.start_new_thread(self._rpyc_server_thread, ())
        # allow time for the rpyc server to start
        # TODO synchronous wait for it to start with a signal
        time.sleep(0.1)

    def stop_server(self):
        """Stop the RPyC server"""
        if not self._rpyc_server:
            logging.warning('can\'t stop the rpyc server because there ' \
                            'isn\'t one running')
            return
        logging.info('stopping RPyC server...')
        self._rpyc_server.close()
        self._rpyc_server = None
        # TODO synchronous wait until thread has exited
        time.sleep(0.1)

    def _rpyc_server_thread(self):
        """Thread for running the RPyC server asynchronously"""
        logging.info('starting RPyC server...')
        self._rpyc_server = ThreadedServer(self, port=self.port,
                            protocol_config={'allow_all_attrs' : True,
                                            'allow_setattr' : True,
                                            'allow_delattr' : True,
                                            'sync_request_timeout' : 10})
        self._rpyc_server.start()
        logging.info('RPyC server stopped')

class CmdPrompt(Cmd):
    """Server shell prompt processor"""
    def __init__(self, inserv):
        super().__init__()
        self.inserv = inserv

    def do_list(self, arg_string):
        """List all the available devices"""
        if arg_string:
            print('Expected 0 args')
            return
        for d in self.inserv.devs.keys():
            print(d)

    def do_update_config(self, arg_string):
        """Reload the server config file\n<string> the config file path"""
        args = arg_string.split(' ')
        if len(args) > 1:
            print('Expected 1 arg: device name, or 0 args for default config')
            return
        # attempt to reload the config file
        try:
            self.inserv.update_config(config_file=\
                                    args[0] if arg_string else None)
        except:
            print('Failed to reload config file')
            return

    def do_reload_dev(self, arg_string):
        """Restart the connection with a device\n<string> the device name"""
        args = arg_string.split(' ')
        if not arg_string or len(args) > 1:
            print('Expected 1 arg: device name')
            return
        dev_name = args[0]
        try:
            self.inserv.reload_device(dev_name)
        except:
            print('Failed to reload device [%s]' % dev_name)
            return

    def do_reload_all(self, arg_string):
        """Restart the connection with all devices"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            self.inserv.reload_devices()
        except:
            print('Failed to reload all devices')
            return

    def do_reload_mongo(self, arg_string):
        """Restart the connection with the mongodb server"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            self.inserv.reload_mongo()
        except:
            print('Failed to reload mongodb server')
            return

    def do_restart(self, arg_string):
        """Restart the server by reloading the config file and all devices"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            self.inserv.restart()
        except:
            print('Failed to restart')
            return

    def do_stop(self, arg_string):
        """Stop the rpyc server"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            self.inserv.stop_server()
        except:
            print('Failed to stop')
            return

    def do_start(self, arg_string):
        """Start the rpyc server"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            self.inserv.start_server()
        except:
            print('Failed to start')
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
        self.inserv.stop_server()
        logging.info('exiting shell...')
        raise SystemExit

if __name__ == '__main__':
    # parse command-line arguments
    arg_parser = argparse.ArgumentParser(prog='inserv',
                            usage='%(prog)s [options]',
                            description='Run an nspyre instrument server')
    arg_parser.add_argument('-c', '--config',
                            default=DEFAULT_CONFIG,
                            help='server configuration file location')
    arg_parser.add_argument('-l', '--log',
                            default=DEFAULT_LOG,
                            help='server log file location')
    arg_parser.add_argument('-m', '--mongo',
                            default=None,
                            help='mongodb address e.g. ' \
                            'mongodb://192.168.1.27:27017/')
    arg_parser.add_argument('-q', '--quiet',
                            action='store_true',
                            help='disable logging')
    arg_parser.add_argument('-v', '--verbose',
                            action='store_true',
                            help='log debug messages')
    cmd_args = arg_parser.parse_args()

    # configure server logging behavior
    if not cmd_args.quiet:
        logging.basicConfig(level=logging.DEBUG if cmd_args.verbose
                        else logging.INFO,
                        format='%(asctime)s -- %(levelname)s -- %(message)s',
                        handlers=[logging.FileHandler(cmd_args.log, 'w+'),
                                logging.StreamHandler()])
    # init and start RPyC server
    logging.info('starting instrument server...')
    inserv = InstrumentServer(cmd_args.config, cmd_args.mongo)

    # start the shell prompt event loop
    cmd_prompt = CmdPrompt(inserv)
    cmd_prompt.prompt = 'inserv > '
    cmd_prompt.cmdloop('instrument server started...')
