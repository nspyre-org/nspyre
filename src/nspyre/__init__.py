import logging

from .data_server import DataSink
from .data_server import DataSource
from .data_server import StreamingList

try:
    from .gui import ColorMapWidget
    from .gui import colors
    from .gui import cyclic_colors
    from .gui import ExperimentWidget
    from .gui import FlexLinePlotWidget
    from .gui import LinePlotWidget
    from .gui import MainWidget
    from .gui import MainWidgetItem
    from .gui import nspyre_font
    from .gui import nspyre_palette
    from .gui import nspyre_style_sheet
    from .gui import nspyreApp
    from .gui import ParamsWidget
    from .gui import qt_set_trace
    from .gui import SaveWidget
    from .gui import QHLine
    from .gui import QVLine
    from .gui import sssss
except ModuleNotFoundError as exc:
    logger = logging.getLogger(__name__)
    logger.warning(
        f'Not importing GUI functionality because the required packages are not installed:\n{exc}'
    )

from .inserv import InstrumentGateway
from .inserv import InstrumentGatewayError
from .inserv import InstrumentServer
from .inserv import InstrumentServerDeviceExistsError
from .inserv import InstrumentServerError
from .cli import inserv_cli
from .cli import dataserv_cli

from .misc import nspyre_init_logger
from .misc import ProcessRunner
from .misc import Q_


__version__ = '0.5.0'
