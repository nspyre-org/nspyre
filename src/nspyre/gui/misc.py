"""
A collection of functionality that doesn't fit anywhere else.

Copyright (c) 2022, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from pdb import set_trace


def qt_set_trace():
    """Set a tracepoint in the Python debugger (pdb) that works with Qt."""
    set_trace()
