#!/usr/bin/env python
"""
This module serves a shell prompt allowing the user runtime control of 
the instrument server

Author: Jacob Feder
Date: 7/8/2020
"""

###########################
# imports
###########################

# std
import argparse
from cmd import Cmd
import pdb
from pathlib import Path
import logging

# 3rd party
import pyvisa

# nspyre
from nspyre.inserv.inserv import InstrumentServer
from nspyre.config.config_files import load_meta_config
from nspyre.definitions import SERVER_META_CONFIG_PATH
from nspyre.misc.logging import nspyre_init_logger

###########################
# globals
###########################

logger = logging.getLogger(__name__)

###########################
# classes / functions
###########################

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
        for d in self.inserv._devs.keys():
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
            logger.exception(exc)
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
            logger.exception(exc)
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
            logger.exception(exc)
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
            logger.exception(exc)
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
            logger.exception(exc)
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
            logger.exception(exc)
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
            logger.exception(exc)
            print('Failed to start server')
            return

    def do_debug(self, arg_string):
        """Drop into the debugging console"""
        if arg_string:
            print('Expected 0 args')
            return
        pdb.set_trace()
        
    def do_quit(self, arg_string):
        """Quit the program"""
        if arg_string:
            print('Expected 0 args')
            return
        logger.info('exiting...')
        # close all open resources
        self.inserv.stop_server()
        for dev_name in list(self.inserv._devs):
            self.inserv.del_device(dev_name)
        pyvisa.ResourceManager().close()
        raise SystemExit

def main():
    """Entry point for instrument server CLI"""

    # parse command-line arguments
    arg_parser = argparse.ArgumentParser(prog='nspyre-inserv',
                            description='Run an nspyre instrument server')
    arg_parser.add_argument('-c', '--config',
                            default=None,
                            help='use the provided config file') 
    arg_parser.add_argument('-l', '--log',
                            default=None,
                            help='log to the provided file / directory')
    arg_parser.add_argument('-q', '--quiet',
                            action='store_true',
                            help='disable logging')
    arg_parser.add_argument('-v', '--verbosity',
                            default='info',
                            help='the verbosity of logging to stdout - options are: '
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
        if cmd_args.log:
            nspyre_init_logger(log_level, log_path=Path(cmd_args.log),
                                        log_path_level=logging.DEBUG,
                                        prefix='inserv')
        else:
            # the user asked for no log file
            nspyre_init_logger(log_level)

    # get the config file
    if cmd_args.config:
        config_path = cmd_args.config
    else:
        config_path = load_meta_config(SERVER_META_CONFIG_PATH)

    # init and start RPyC server
    logger.info('starting instrument server...')
    inserv = InstrumentServer(config_path)

    # start the shell prompt event loop
    cmd_prompt = InservCmdPrompt(inserv)
    cmd_prompt.prompt = 'inserv > '
    cmd_prompt.cmdloop('instrument server started...')

###########################
# standalone main
###########################

if __name__ == '__main__':
    main()