#!/usr/bin/env python
"""
    nspyre.gui.__init__.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    This module runs the main nspyre GUI, which allows the user to easily
    launch other tools

    Author: Alexandre Bourassa
    Modified: Jacob Feder 7/25/2020, Michael Solomon 9/12/2020
"""

import argparse
import logging
from pathlib import Path
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from .app import NSpyreApp
from .main_window import NSpyreMainWindow

THIS_DIR = Path(__file__).parent
DEFAULT_LOG = THIS_DIR / 'nspyre.log'

###########################
# standalone main
###########################

def main(args=None):
    """Entry point for the application script"""
    # parse command-line arguments
    arg_parser = argparse.ArgumentParser(prog='nspyre',
                            usage='%(prog)s [options]',
                            description='Run the nspyre GUI')
    arg_parser.add_argument('-c', '--config', nargs='+',
                            default=None,
                            help='permanently add a configuration '
                            'file(s) to the list to be imported on startup')
    arg_parser.add_argument('-d', '--delete-config', nargs='+',
                            default=None,
                            help='remove a configuration file(s) from '
                            'the list to be imported on startup')
    arg_parser.add_argument('-e', '--list_configs',
                            action='store_true',
                            help='list the configuration files to be '
                            'imported on startup')
    arg_parser.add_argument('-l', '--log',
                            default=DEFAULT_LOG,
                            help='log to the provided file location')
    arg_parser.add_argument('-m', '-- ',
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

    # configure logging behavior
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
            raise Exception('didn\'t recognize logging level [%s]' \
                                        % (cmd_args.verbosity)) from None

        logging.basicConfig(level=log_level,
                        format='%(asctime)s -- %(levelname)s -- %(message)s',
                        handlers=[logging.FileHandler(cmd_args.log, 'w+'),
                                logging.StreamHandler()])

    logging.info('starting NSpyre...')
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = NSpyreApp([sys.argv])
    main_window = NSpyreMainWindow()
    sys.exit(app.exec())
