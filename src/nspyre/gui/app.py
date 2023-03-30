"""
nspyre application Qt GUI settings.
"""
import gc
import logging
import sys
from pathlib import Path

from pyqtgraph import _connectCleanup
from pyqtgraph import setConfigOptions
from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

from .style._style import nspyre_font
from .style._style import nspyre_palette
from .style._style import nspyre_style_sheet

_logger = logging.getLogger(__name__)

_HERE = Path(__file__).parent


class nspyreApp(QtWidgets.QApplication):
    """Create a Qt application object with the default nspyre settings.

    Typical usage example:

    .. code-block:: python

        from nspyre import nspyreApp

        app = nspyreApp()
        some_widget = SomeWidget()
        some_widget.show()
        app.exec()

    """

    def __init__(
        self,
        app_name: str = 'nspyre',
        palette: QtGui.QPalette = nspyre_palette,
        font: QtGui.QFont = nspyre_font,
    ):
        """
        Args:
            app_name: Display name of the application.
            palette: Qt palette.
            font: QFont to use for the application.
        """
        # for high DPI displays in Qt5
        if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
            QtCore.QCoreApplication.setAttribute(
                QtCore.Qt.AA_EnableHighDpiScaling, True
            )
        if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
            QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

        super().__init__(sys.argv)

        self.setApplicationName(app_name)
        # dock icon
        icon_path = _HERE / 'images' / 'favicon.ico'
        self.setWindowIcon(QtGui.QIcon(str(icon_path)))

        # make sure pyqtgraph gets cleaned up properly
        _connectCleanup()
        # enable plot antialiasing
        setConfigOptions(antialias=True)

        # appearance settings for nspyre
        self.setStyle(QtWidgets.QStyleFactory.create('Fusion'))
        self.setPalette(palette)
        self.setStyleSheet(nspyre_style_sheet)
        self.setFont(font)

    def exec(self, *args, **kwargs):
        """Run the GUI event loop."""
        try:
            super().exec(*args, **kwargs)
        except AttributeError:
            super().exec_(*args, **kwargs)
        # invoke garbage collector to make sure we don't get any false leak reports
        gc.collect()
        # report Qt leaks
        leaked_widgets = self.allWidgets()
        if leaked_widgets:
            leaked_str = f'Leaked {len(leaked_widgets)} Qt widgets:\n'
            for w in leaked_widgets:
                leaked_str += repr(w) + '\n'
            _logger.debug(leaked_str)
        else:
            _logger.debug('No Qt widgets leaked.')
