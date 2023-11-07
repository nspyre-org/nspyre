import logging
from typing import Any

_logger = logging.getLogger(__name__)

try:
    from pyqtgraph.Qt import QtCore
except ModuleNotFoundError:
    _logger.info(
        'Not importing GUI functionality because the required packages are not '
        'installed.'
    )
    Qt_GUI: bool = False
    """True if the packages for a Qt GUI are installed."""
    QObject: Any = object
    QtCore = None
else:
    Qt_GUI = True
    QObject = QtCore.QObject
    """If Qt GUI packages are installed, this is Qt :code:`QObject`, otherwise it is
    equal to python :code:`object`."""

    from .app import nspyre_font
    from .app import nspyre_palette
    from .app import nspyre_style_sheet
    from .app import nspyreApp
    from .debug import qt_set_trace
    from .style import colors
    from .style import cyclic_colors
    from .threadsafe import QThreadSafeObject
    from .threadsafe import run_threadsafe
    from .widgets import HeatMapWidget
    from .widgets import experiment_widget_process_queue
    from .widgets import ExperimentWidget
    from .widgets import FlexLinePlotWidget
    from .widgets import LinePlotWidget
    from .widgets import LoadWidget
    from .widgets import MainWidget
    from .widgets import MainWidgetItem
    from .widgets import ParamsWidget
    from .widgets import SaveLoadWidget
    from .widgets import QHLine
    from .widgets import QVLine
    from .widgets import sssss
