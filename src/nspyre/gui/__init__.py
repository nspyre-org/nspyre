import logging
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from nspyre.misc import nspyre_init_logger

from .app import NSpyreApp
from .main_window import NSpyreMainWindow

from .colors import colors
from .data_handling import save_data
from .widgets.plotting import HeatmapPlotWidget, LinePlotWidget
from .widgets.views import Plot1D, Plot2D, PlotFormatInit, PlotFormatUpdate

__all__ = [
    'HeatmapPlotWidget',
    'LinePlotWidget',
    'Plot1D',
    'Plot2D',
    'PlotFormatInit',
    'PlotFormatUpdate',
    'colors',
    'save_data',
]

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
