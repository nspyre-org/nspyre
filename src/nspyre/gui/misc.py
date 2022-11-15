"""
A collection of miscellaneous functionality for GUIs.
"""
import logging
from pdb import set_trace

logger = logging.getLogger(__name__)

try:
    from pyqtgraph.Qt.QtCore import pyqtRemoveInputHook
except ImportError:
    qt_remove_hook = False
    logger.debug(
        'Ignoring Qt remove hook because the PyQt implementation doesn\'t required it.'
    )
else:
    qt_remove_hook = True
    logger.debug('Using PyQt remove input hook.')


def qt_set_trace():
    """Set a tracepoint in the Python debugger (pdb) that works with Qt."""
    if qt_remove_hook:
        pyqtRemoveInputHook()
    set_trace()
