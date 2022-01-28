"""
NSpyre application Qt GUI settings.

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import gc
import logging
import sys
from pathlib import Path

import pyqtgraph as pg
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QStyleFactory

from .style.style import nspyre_font
from .style.style import nspyre_palette
from .style.style import nspyre_style_sheet

logger = logging.getLogger(__name__)

HERE = Path(__file__).parent


class NspyreApp(QApplication):
    """Create a Qt application object with the default nspyre settings.

    Typical usage example:

    .. code-block:: python

        from nspyre import NspyreApp

        app = NspyreApp()
        some_widget = SomeWidget()
        some_widget.show()
        # run the GUI event loop
        app.exec()

    """

    def __init__(self, app_name: str = 'nspyre', font: QFont = nspyre_font):
        """
        Args:
            app_name: display name of the application.
            font: QFont to use for the application.
        """
        # for high DPI displays
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        super().__init__(sys.argv)

        self.setApplicationName(app_name)
        # dock icon
        icon_path = HERE / 'images' / 'favicon.ico'
        self.setWindowIcon(QIcon(str(icon_path)))

        # make sure pyqtgraph gets cleaned up properly
        pg._connectCleanup()
        # enable plot antialiasing
        pg.setConfigOptions(antialias=True)

        # appearance settings for nspyre
        fusion = QStyleFactory.create('Fusion')
        self.setStyle(fusion)
        self.setPalette(nspyre_palette)
        self.setStyleSheet(nspyre_style_sheet)
        self.setFont(font)

    def exec(self, *args, **kwargs):
        super().exec(*args, **kwargs)
        # invoke garbage collector to make sure we don't get any false leak reports
        gc.collect()
        # report Qt leaks
        leaked_widgets = self.allWidgets()
        if leaked_widgets:
            leaked_str = f'Leaked {len(leaked_widgets)} Qt widgets:\n'
            for w in leaked_widgets:
                leaked_str += repr(w) + '\n'
            logger.debug(leaked_str)
        else:
            logger.debug('No Qt widgets leaked.')
