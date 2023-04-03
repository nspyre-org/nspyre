try:
    from pyqtgraph.Qt import QtCore
except ModuleNotFoundError:
    _logger = logging.getLogger(__name__)
    _logger.info(
        f'Not importing GUI functionality because the required packages are not installed.'
    )
    QObject = object
    Qt_GUI = False
else:
    QObject = QtCore.QObject
    Qt_GUI = True

    from .app import nspyre_font
    from .app import nspyre_palette
    from .app import nspyre_style_sheet
    from .app import nspyreApp
    from .misc import qt_set_trace
    from .style import colors
    from .style import cyclic_colors
    from .widgets import *
