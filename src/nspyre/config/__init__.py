#!/usr/bin/env python
"""
CLI for setting the config files

Author: Jacob Feder
Date: 9/13/2020
"""

###########################
# imports
###########################

# std
import argparse
import logging
from pathlib import Path

# nspyre
from nspyre.definitions import CLIENT_META_CONFIG_PATH, SERVER_META_CONFIG_PATH
from nspyre.config.config_files import meta_config_add, meta_config_remove, \
                                meta_config_files

###########################
# globals
###########################

THIS_DIR = Path(__file__).parent
DEFAULT_LOG = THIS_DIR / 'config.log'

###########################
# exceptions
###########################

class NSpyreConfigError(Exception):
    pass

###########################
# classes / functions
###########################

def main():
    """Entry point for instrument server CLI"""
    # parse command-line arguments
    arg_parser = argparse.ArgumentParser(prog='nspyre-config',
                            description='Set the nspyre configuration files')
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
    arg_parser.add_argument('-q', '--quiet',
                            action='store_true',
                            help='disable logging')
    arg_parser.add_argument('-v', '--verbosity',
                            default='info',
                            help='the verbosity of logging - options are: '
                            'debug, info, warning, error')
    arg_parser.add_argument('client_or_server', help='pass [client] to modify '
        'the client configuration files, [server] for the instrument server')
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
            raise Exception('didn\'t recognize logging level [{}]'.\
                                        format(cmd_args.verbosity)) from None

        logging.basicConfig(level=log_level,
                        format='%(asctime)s -- %(levelname)s -- %(message)s',
                        handlers=[logging.FileHandler(cmd_args.log, 'w+'),
                                logging.StreamHandler()])

    if cmd_args.client_or_server == 'client':
        meta_config_path = CLIENT_META_CONFIG_PATH
    elif cmd_args.client_or_server == 'server':
        meta_config_path = SERVER_META_CONFIG_PATH
    else:
        raise NSpyreConfigError('expected either [client] or [server]')

    if cmd_args.config:
        # the user asked us to add config files to the meta-config
        meta_config_add(meta_config_path, cmd_args.config)
        return
    if cmd_args.delconfig:
        # the user asked us to remove config files from the meta-config
        meta_config_remove(meta_config_path, cmd_args.delconfig)
        return
    if cmd_args.list_configs:
        # the user asked us to list the config files from the meta-config
        files  = meta_config_files(meta_config_path)
        for i in range(len(files)):
            print('{}: {}'.format(i, files[i]))
        return

###########################
# standalone main
###########################

if __name__ == '__main__':
    main()
