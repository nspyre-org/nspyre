"""
This module defines basic constants and functions that will be used
throughout nspyre

Author: Jacob Feder
Date: 7/8/2020
"""

###########################
# imports
###########################

# std
import os
from pathlib import Path

# 3rd party
from pint import UnitRegistry

###########################
# fundamental operations
###########################

# create a pint registry universal to nspyre
ureg = UnitRegistry()
Q_ = ureg.Quantity

# root directory of nspyre
NSPYRE_ROOT = Path(__file__).parent

def join_nspyre_path(path):
    """Return a full path from a path given relative to the nspyre root 
    directory"""
    return NSPYRE_ROOT / path

###########################
# resources
###########################

# config files
CLIENT_META_CONFIG_PATH = join_nspyre_path('config/client_meta_config.yaml')
SERVER_META_CONFIG_PATH = join_nspyre_path('config/server_meta_config.yaml')

# images
LOGO_PATH = str(join_nspyre_path('gui/images/spyre.png'))

###########################
# globals
###########################

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
# rpyc connection timeout in s
RPYC_CONN_TIMEOUT = None
# rpyc send/receive timeout in s
RPYC_SYNC_TIMEOUT = None

# config file key for mongodb address
CONFIG_MONGO_ADDR_KEY = 'mongodb_addr'
