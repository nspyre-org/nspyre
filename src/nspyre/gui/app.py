"""The class defining the NSpyre Application.

The NSpyreApp class is the entry point for the NSpyre software application.
It is defined by the QtWidgets.QApplication subclass from Qt and defines
all the parameters for setting up the Qt GUI.

From the Qt documentation:
The QApplication class manages the GUI application's control flow and main settings.
It contains the main event loop, where all events from the window system and other
sources are processed and dispatched. It also handles the application's initialization
and finalization, and provides session management. It also handles most system-wide
and application-wide settings. For any GUI application that uses Qt, there is
precisely one QApplication object, no matter whether the application has 0, 1, 2 or
more windows at any time.

  Typical usage example:

  app = NSpyreApp([sys.argv])
  window = main_window.NSpyreMainWindow()
  sys.exit(app.exec())

Copyright (c) 2020, Alexandre Bourassa, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QPalette
from PyQt5.QtWidgets import QApplication, QStyleFactory

HERE = Path(__file__).parent


class NSpyreApp(QApplication):
    """The Qt QtWidgets.QApplication object for launching NSpyre.

    This is the class you need to instantiate for starting a Qt GUI.
    This has the additional settings and parameters determining the
    appearance of the GUI application.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setApplicationName('NSpyre')
        icon_path = HERE / 'images/favicon.ico'
        self.setWindowIcon(QIcon(str(icon_path)))
        self.set_theme()

    def set_theme(self):
        """A method containing the appearance settings for NSpyre."""
        fusion = QStyleFactory.create('Fusion')
        self.setStyle(fusion)
        dark = QColor(53, 53, 53) #(61, 64, 62) (196,201,201)
        palette = QPalette()
        palette.setColor(QPalette.Window, dark)
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, dark)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, dark)
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)
        style_sheet = (HERE / 'style.css').read_text()
        self.setStyleSheet(style_sheet)
        self.setFont(QFont('Helvetica [Cronyx]'))
