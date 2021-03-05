"""The class defining the NSpyre MainWindow.

The NSpyreMainWindow class is the main GUI window for the NSpyre software application.
It is defined by the QtWidgets.QMainWindow subclass from Qt and defines
the process for launching all the other QtWidgets.QtWidget for the other GUI windows.
i.e. Instrument Manager, View Manager, Spyrelet Launcher, etc.

From the Qt documentation:
The QMainWindow class provides a main application window, with a menu bar, dock
windows (e.g. for toolbars), and a status bar. Main windows are most often used to
provide menus, toolbars and a status bar around a large central widget, such as a
text edit, drawing canvas or QWorkspace (for MDI applications). QMainWindow is
usually subclassed since this makes it easier to encapsulate the central widget,
menus and toolbars as well as the window's state. Subclassing makes it possible to
create the slots that are called when the user clicks menu items or toolbar buttons.

  Typical usage example:

  app = app.NSpyreApp([sys.argv])
  window = NSpyreMainWindow()
  sys.exit(app.exec())

Copyright (c) 2020, Alexandre Bourassa, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import functools
from pathlib import Path
import logging
from subprocess import Popen

from PyQt5.QtCore import QProcess
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget

from nspyre.definitions import LOGO_PATH
from nspyre.gui.image import ImageWidget

logger = logging.getLogger(__name__)

HERE = Path(__file__).parent


class NSpyreMainWindow(QMainWindow):
    """The Qt QtWidgets.QMainWindow object for launching NSpyre.

    This is the class you need to instantiate for starting the main
    NSpyre GUI. This defines the layout of the NSpyre launcher and
    is responsible for correctly starting the Qt Widgets for the
    additional GUI windows in NSpyre.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('NSpyre')

        # Set the main window layout to consist of vertical boxes.
        # The QVBoxLayout class lines up widgets vertically.
        layout = QVBoxLayout()

        # Add the NSpyre launcher logo as the top GUI element
        image = ImageWidget(LOGO_PATH)
        layout.addWidget(image)

        # Add a QtPushButton element for launching each additional
        # GUI window and connect a function for launching each
        # Qt Widget correctly
        inserv_manager_button = QPushButton('Instrument Manager', self)
        inserv_manager_button.setFont(QFont('Helvetica [Cronyx]', 16))
        inserv_manager_button.clicked.connect(
            functools.partial(self._launch_window, window_name='inserv_manager'))

        view_manager_button = QPushButton('View Manager', self)
        view_manager_button.setFont(QFont('Helvetica [Cronyx]', 16))
        view_manager_button.clicked.connect(
            functools.partial(self._launch_window, window_name='view_manager'))

        spyrelet_startup_button = QPushButton('Startup Spyrelet(s)', self)
        spyrelet_startup_button.setFont(QFont('Helvetica [Cronyx]', 16))
        spyrelet_startup_button.clicked.connect(
            functools.partial(self._launch_window, window_name='spyrelet_startup'))

        data_explorer_button = QPushButton('Data Explorer', self)
        data_explorer_button.setFont(QFont('Helvetica [Cronyx]', 16))
        data_explorer_button.clicked.connect(
            functools.partial(self._launch_window, window_name='data_explorer'))

        # add each button to the box layout as a widget
        layout.addWidget(inserv_manager_button)
        layout.addWidget(view_manager_button)
        layout.addWidget(spyrelet_startup_button)
        layout.addWidget(data_explorer_button)

        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.show()

    def _launch_window(self, window_name=None):
        """Spawn an additional window in a new process."""

        if window_name == 'inserv_manager':
            logger.info('starting Instrument Manager...')
            Popen(['python', str(HERE.joinpath('instrument_manager.py'))])
        elif window_name == 'view_manager':
            logger.info('starting View Manager...')
            Popen(['python', str(HERE.joinpath('view_manager.py'))])
        elif window_name == 'spyrelet_startup':
            logger.info('starting Syrelet GUI window...')
            Popen(['python', str(HERE.joinpath('launcher.py'))])
        elif window_name == 'data_explorer':
            logger.info('starting Data Explorer...')
            Popen(['python', str(HERE.joinpath('data_explorer.py'))])
        else:
            raise ValueError('Incorrect input for window_name: {}'.format(window_name))
