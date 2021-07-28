from pathlib import Path

from .inserv import InstrumentServer, InstrumentGateway, InstrumentServerError, InstrumentGatewayError
from .dataserv import DataSource, DataSink, SINK_DATA_TYPE_DEFAULT, SINK_DATA_TYPE_DELTA, SINK_DATA_TYPE_PICKLE
from .misc import nspyre_init_logger, qt_set_trace, Q_

# root directory of nspyre
NSPYRE_ROOT = Path(__file__).parent

def join_nspyre_path(path):
    """Return a full path from a path given relative to the nspyre root 
    directory"""
    return NSPYRE_ROOT / path

# images
LOGO_PATH = str(join_nspyre_path('gui/images/spyre.png'))

__all__ = [
    'InstrumentServer',
    'InstrumentGateway',
    'InstrumentServerError',
    'InstrumentGatewayError',
    'DataSource',
    'DataSink',
    'SINK_DATA_TYPE_DEFAULT',
    'SINK_DATA_TYPE_DELTA',
    'SINK_DATA_TYPE_PICKLE',
    'nspyre_init_logger',
    'qt_set_trace',
    'Q_'
]

__version__ = '0.5.0'
