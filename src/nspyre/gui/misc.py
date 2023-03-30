"""
A collection of miscellaneous functionality for Qt GUIs.
"""

import logging
from pdb import set_trace

_logger = logging.getLogger(__name__)

try:
    from pyqtgraph.Qt.QtCore import pyqtRemoveInputHook
except ImportError:
    _qt_remove_hook = False
    _logger.debug(
        'Ignoring Qt remove hook because the PyQt implementation doesn\'t required it.'
    )
else:
    _qt_remove_hook = True
    _logger.debug('Using PyQt remove input hook.')


def qt_set_trace():
    """Set a tracepoint in the Python debugger (pdb) that works with Qt."""
    if _qt_remove_hook:
        pyqtRemoveInputHook()
    set_trace()
