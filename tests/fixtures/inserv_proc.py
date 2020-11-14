#!/usr/bin/env python

"""
This module runs the instrument server forever. The config file location should be
passed as an argument.

Author: Jacob Feder
Date: 11/12/2020
"""

###########################
# imports
###########################

# std
import logging
import sys
import time
from pathlib import Path

# nspyre
from nspyre.inserv.inserv import InstrumentServer
from nspyre.definitions import NSPYRE_LOG_FMT

###########################
# main
###########################

# set up the logging
logging.basicConfig(level=logging.DEBUG,
                format=NSPYRE_LOG_FMT,
                handlers=[logging.StreamHandler()])

cfg_path = Path(sys.argv[1])
# resolve relative paths
if not cfg_path.is_absolute():
    cfg_path = (Path.cwd() / cfg_path).resolve()

# run the server in background
inserv = InstrumentServer(cfg_path)

# serve forever
while True:
    time.sleep(0.1)
