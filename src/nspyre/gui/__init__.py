import logging
import sys

from nspyre.misc import nspyre_init_logger
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from .app import NSpyreApp
from .colors import colors
from .data_handling import save_data
from .main_window import NSpyreMainWindow
from .widgets.plotting import HeatmapPlotWidget
from .widgets.plotting import LinePlotWidget
from .widgets.views import Plot1D
from .widgets.views import Plot2D
from .widgets.views import PlotFormatInit
from .widgets.views import PlotFormatUpdate


logger = logging.getLogger(__name__)


def main(args=None):
    """Entry point for the application script."""

    nspyre_init_logger(logging.INFO)
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = NSpyreApp(['NSpyre', sys.argv])
    main_window = NSpyreMainWindow()
    sys.exit(app.exec())
