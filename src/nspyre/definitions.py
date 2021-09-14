"""
This module defines basic constants and functions that will be used
throughout nspyre

Copyright (c) 2020, Alexandre Bourassa, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""

from pathlib import Path

from pint import get_application_registry


# create a pint registry universal to nspyre
# uses get_application_registry to check if one
# already exists before creating a new instance
ureg = get_application_registry()
Q_ = ureg.Quantity

# root directory of nspyre
NSPYRE_ROOT = Path(__file__).parent


def join_nspyre_path(path):
    """Return a full path from a path given relative to the nspyre root 
    directory"""
    return NSPYRE_ROOT / path


# config files
CLIENT_META_CONFIG_PATH = join_nspyre_path('config/client_meta_config.yaml')
SERVER_META_CONFIG_PATH = join_nspyre_path('config/server_meta_config.yaml')

# images
LOGO_PATH = str(join_nspyre_path('gui/images/spyre.png'))


# format for accessing instrument server devices from a client, where the first
# item is the server name and the second is the device name (both defined in the
# server config file)
INSERV_DEV_ACCESSOR = '{}/{}'
# mongodb replicaset name
MONGO_RS = 'NSpyreSet'
# all spyrelet databases in mongodb will be of this form
MONGO_SPYRELETS_KEY = 'spyrelet[{}]'
# mongodb instrument server databases will contain a special document
# that contains the instrument server settings
MONGO_SERVERS_SETTINGS_KEY = '_settings'
# All instrument server databases in mongodb will be of this form
MONGO_SERVERS_KEY = 'inserv[{}]'
# in ms
MONGO_CONNECT_TIMEOUT = 5000
# rpyc connection timeout in s (None for no timeout)
RPYC_CONN_TIMEOUT = 30
# rpyc send/receive timeout in s (don't set to None)
RPYC_SYNC_TIMEOUT = 30

# config file key for mongodb address
CONFIG_MONGO_ADDR_KEY = 'mongodb_addr'
