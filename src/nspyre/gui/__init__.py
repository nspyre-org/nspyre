import logging

try:
    from pyqtgraph.Qt import QtCore
except ModuleNotFoundError:
    _logger = logging.getLogger(__name__)
    _logger.info(
        'Not importing GUI functionality because the required packages are not installed.'
    )
    Qt_GUI = False
else:
    Qt_GUI = True

if Qt_GUI:
    from .app import nspyre_font
    from .app import nspyre_palette
    from .app import nspyre_style_sheet
    from .app import nspyreApp
    from .debug import qt_set_trace
    from .style import colors
    from .style import cyclic_colors
    from .widgets import ColorMapWidget
    from .widgets import experiment_widget_process_queue
    from .widgets import ExperimentWidget
    from .widgets import FlexLinePlotWidget
    from .widgets import LinePlotWidget
    from .widgets import LoadWidget
    from .widgets import MainWidget
    from .widgets import MainWidgetItem
    from .widgets import ParamsWidget
    from .widgets import SaveWidget
    from .widgets import QHLine
    from .widgets import QVLine
    from .widgets import sssss

    QObject = QtCore.QObject
else:
    QObject = object
    QtCore = None
