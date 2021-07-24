"""
This module defines basic constants and functions that will be used
throughout nspyre

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""

from pathlib import Path

from pint import get_application_registry

# create a pint registry universal to nspyre
ureg = get_application_registry()
Q_ = ureg.Quantity

# root directory of nspyre
NSPYRE_ROOT = Path(__file__).parent

def join_nspyre_path(path):
    """Return a full path from a path given relative to the nspyre root 
    directory"""
    return NSPYRE_ROOT / path

# images
LOGO_PATH = str(join_nspyre_path('gui/images/spyre.png'))

# default instrument server port
INSERV_DEFAULT_PORT = 42068
# rpyc connection timeout in s
RPYC_CONN_TIMEOUT = None
# rpyc send/receive timeout in s
RPYC_SYNC_TIMEOUT = None

# max size of a log file (in bytes) before creating a new one
LOG_FILE_MAX_SIZE = 100e6

# default port to host the data server on
DATASERV_PORT = 30000
