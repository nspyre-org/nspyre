#!/usr/bin/env python
"""
    nspyre.gui.__init__.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    This module runs the main nspyre GUI, which allows the user to easily
    launch other tools

    Author: Alexandre Bourassa
    Modified: Jacob Feder 7/25/2020, Michael Solomon 9/12/2020
"""

###########################
# imports
###########################

# std
import logging
import os
import time
from subprocess import Popen
import argparse
from pathlib import Path

# 3rd party
from PyQt5 import QtCore, QtWidgets

# nspyre
from nspyre.gui.image import ImageWidget
from nspyre.definitions import join_nspyre_path, LOGO_PATH

###########################
# globals
###########################

THIS_DIR = Path(__file__).parent
DEFAULT_LOG = THIS_DIR / 'nspyre.log'

###########################
# exceptions
###########################

###########################
# classes
###########################

class NSpyre_Launcher(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        
        main_layout = QtWidgets.QVBoxLayout()
        im = ImageWidget(LOGO_PATH)
        main_layout.addWidget(im)

        # btn_widget = QtWidgets.QWidget()
        # btn_layout = QtWidgets.QHBoxLayout()

        #self.inst_server_btn = QtWidgets.QPushButton('Start Instrument Server')
        self.inst_manager_btn = QtWidgets.QPushButton('Start Instrument Manager')
        self.view_manager_btn = QtWidgets.QPushButton('Start View Manager')
        self.spyrelet_launcher_btn = QtWidgets.QPushButton('Start Spyrelet Launcher')
        self.data_explorer_btn = QtWidgets.QPushButton('Data Explorer')

        #main_layout.addWidget(self.inst_server_btn)
        main_layout.addWidget(self.inst_manager_btn)
        main_layout.addWidget(self.view_manager_btn)
        main_layout.addWidget(self.spyrelet_launcher_btn)
        main_layout.addWidget(self.data_explorer_btn)

        #self.inst_server_btn.clicked.connect(lambda: self.launch('instrument_server.py', new_console=True))
        self.inst_manager_btn.clicked.connect(lambda: \
            self.launch(join_nspyre_path('gui/instrument_manager.py')))
        self.view_manager_btn.clicked.connect(lambda: self.launch('gui/view_manager.py'))
        self.spyrelet_launcher_btn.clicked.connect(lambda: self.launch('gui/launcher.py'))
        self.data_explorer_btn.clicked.connect(lambda: self.launch('gui/data_explorer.py'))

        self.setLayout(main_layout)
    
    def launch(self, nspyre_py_file, new_console=False):
        if new_console:
            pass
            # TODO cross-platform
            # filename = os.path.normpath(join_nspyre_path(nspyre_py_file))
            # filename = filename.replace('\\', '/')
            # cmd = 'bash -c "activate {}; python {}"'.format(get_configs()['conda_env'], filename)
            # Popen(cmd, shell=True)
        else:
            Popen(['python', join_nspyre_path(nspyre_py_file)])


###########################
# standalone main
###########################

def main(args=None):
    """Entry point for the application script"""
    from nspyre.gui.app import NSpyreApp
    # parse command-line arguments
    arg_parser = argparse.ArgumentParser(prog='nspyre',
                            usage='%(prog)s [options]',
                            description='Run the nspyre GUI')
    arg_parser.add_argument('-c', '--config', nargs='+',
                            default=None,
                            help='permanently add a configuration '
                            'file(s) to the list to be imported on startup')
    arg_parser.add_argument('-d', '--delconfig', nargs='+',
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

    logging.info('starting nspyre...')
    app = NSpyreApp([])
    w = NSpyre_Launcher()
    w.show()
    app.exec_()
