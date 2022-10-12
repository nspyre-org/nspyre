"""
A collection of functionality that doesn't fit anywhere else.

Copyright (c) 2022, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
from pdb import set_trace

logger = logging.getLogger(__name__)

try:
    from pyqtgraph.Qt.QtCore import pyqtRemoveInputHook
except ImportError as err:
    qt_remove_hook = False
    logger.debug(f'Ignoring Qt remove hook because the PyQt implementation doesn\'t required it.')
else:
    qt_remove_hook = True
    logger.debug(f'Using PyQt remove input hook.')

def qt_set_trace():
    """Set a tracepoint in the Python debugger (pdb) that works with Qt."""
    if qt_remove_hook:
        pyqtRemoveInputHook()
    set_trace()
