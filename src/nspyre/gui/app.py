"""
NSpyre application Qt GUI settings.

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from pathlib import Path

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QStyleFactory
from pyqtgraph import _connectCleanup as pyqtgraph_connectCleanup

HERE = Path(__file__).parent


def nspyre_app(argv: list[str], app_name: str = 'NSpyre'):
    """Apply default nspyre settings to a Qt application object.

    Args:
        argv: pass sys.argv.
        app_name: display name of the application.

    Typical usage example:

    .. code-block:: python

        from nspyre import nspyre_app
        app = QApplication(sys.argv)
        nspyre_app(app)

    """

    # for high DPI displays
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(argv)

    app.setApplicationName(app_name)
    icon_path = HERE / 'images' / 'favicon.ico'
    app.setWindowIcon(QIcon(str(icon_path)))

    pyqtgraph_connectCleanup()

    # appearance settings for nspyre
    fusion = QStyleFactory.create('Fusion')
    app.setStyle(fusion)
    dark = QColor(53, 53, 53)  # (61, 64, 62) (196,201,201)
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
    app.setPalette(palette)
    style_sheet = (HERE / 'style' / 'style.qss').read_text()
    app.setStyleSheet(style_sheet)
    app.setFont(QFont('Helvetica [Cronyx]'))

    return app
