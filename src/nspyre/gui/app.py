"""
NSpyre application Qt GUI settings.

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from pathlib import Path

import pyqtgraph as pg
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QStyleFactory

from .style.style import nspyre_font
from .style.style import nspyre_palette
from .style.style import nspyre_style_sheet


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

    pg._connectCleanup()
    # enable antialiasing
    pg.setConfigOptions(antialias=True)

    # appearance settings for nspyre
    fusion = QStyleFactory.create('Fusion')
    app.setStyle(fusion)

    app.setPalette(nspyre_palette)
    app.setStyleSheet(nspyre_style_sheet)
    app.setFont(nspyre_font)

    return app
