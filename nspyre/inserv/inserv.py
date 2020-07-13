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
import rpyc
import os
import _thread
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
    
    def __init__(self, config_file):
        super().__init__()
        self.config = {}
        self.update_config(config_file)
        self.name = get_config_param(self.config, ['server_settings', 'name'])
        self.port = get_config_param(self.config, ['server_settings', 'port'])
        self.devs = {}
        self.reload_devices()

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
            self.devs[dev_name] = dev_class(*dev_args, **dev_kwargs)
        except:
            raise InstrumentServerError('Failed to get instance of device ' \
                                        '[%s] of class [%s]'
                                        % (dev_name, dev_class)) from None

        # initialize it
        try:
            self.devs[dev_name].initialize()
        except:
            raise InstrumentServerError('Device [%s] initialization sequence' \
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

    def update_config(self, config_file):
        """Reload the config file"""
        filename = os.path.join(this_dir, config_file)
        self.config = load_config(filename)

    def on_connect(self, conn):
        pass

    def on_disconnect(self, conn):
        pass

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
        """Reload the server config file\n- the config file location"""
        args = arg_string.split(' ')
        if not arg_string:
            filename = DEFAULT_CONFIG
        else:
            # deal with absolute vs relative paths
            filename = args[0]
            if not os.path.isabs(args[0]):
                filename = os.path.join(os.getcwd(), filename)

        # attempt to reload the config file
        try:
            self.inserv.update_config(filename)
        except:
            print('Failed to reload config file')
            return
        print('Reloaded config file')

    def do_reload(self, arg_string):
        """Restart the connection with a device\n- the device name string"""
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
        print('Reloaded device [%s]' % dev_name)

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
        print('Reloaded all devices')

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
        logging.info('Exiting...')
        raise SystemExit

def rpyc_server_thread(inserv):
    """Thread for running the RPyC server asynchronously"""
    t = ThreadedServer(inserv, port=inserv.port,
                        protocol_config={'allow_all_attrs' : True,
                                        'allow_setattr' : True,
                                        'allow_delattr' : True,
                                        'sync_request_timeout' : 10})
    t.start()

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
    arg_parser.add_argument('-q', '--quiet',
                            action='store_true',
                            help='disable logging')
    cmd_args = arg_parser.parse_args()

    # configure server logging behavior
    if not cmd_args.quiet:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s -- %(levelname)s -- %(message)s',
                            handlers=[logging.FileHandler(cmd_args.log, 'w+'),
                                        logging.StreamHandler()])
    # start RPyC server
    logging.info('starting instrument server...')
    inserv = InstrumentServer(cmd_args.config)
    _thread.start_new_thread(rpyc_server_thread, (inserv,))
    
    # allow time for the rpyc server to start
    time.sleep(0.1)
    
    # start the shell prompt event loop
    cmd_prompt = CmdPrompt(inserv)
    cmd_prompt.prompt = 'inserv > '
    cmd_prompt.cmdloop('instrument server started...')
