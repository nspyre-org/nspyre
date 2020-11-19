#!/usr/bin/env python
"""
    nspyre.gui.__init__.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    This module runs the main nspyre GUI, which allows the user to easily
    launch other tools

    Author: Alexandre Bourassa
    Modified: Jacob Feder 7/25/2020, Michael Solomon 9/12/2020
"""

import logging
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from .app import NSpyreApp
from .main_window import NSpyreMainWindow

from nspyre.misc.logging import nspyre_init_logger

###########################
# globals
###########################

logger = logging.getLogger(__name__)

###########################
# standalone main
###########################

def main(args=None):
    """Entry point for the application script"""

    nspyre_init_logger(logging.INFO)

    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = NSpyreApp([sys.argv])
    main_window = NSpyreMainWindow()
    sys.exit(app.exec())
