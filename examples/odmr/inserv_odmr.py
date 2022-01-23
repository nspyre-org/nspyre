#!/usr/bin/env python
"""
Start up an instrument server and load drivers for ODMR experiments.

Author: Jacob Feder
Date: 12/27/2021
"""
import logging
from pathlib import Path

from nspyre import InservCmdPrompt
from nspyre import InstrumentServer
from nspyre import nspyre_init_logger

HERE = Path(__file__).parent

# log to the console as well as a file inside the logs folder
nspyre_init_logger(
    logging.INFO,
    log_path=HERE / 'logs',
    log_path_level=logging.DEBUG,
    prefix='odmr_inserv',
    file_size=10_000_000,
)

# create a new instrument server
with InstrumentServer() as inserv:
    # signal generator
    inserv.add('sg', HERE / 'drivers' / 'sg.py', 'SigGen')
    # data acquisition instrument
    inserv.add('daq', HERE / 'drivers' / 'daq.py', 'DAQ')

    # run a CLI (command-line interface) that allows the user to enter
    # commands to control the server
    cmd_prompt = InservCmdPrompt(inserv)
    cmd_prompt.prompt = 'inserv > '
    try:
        cmd_prompt.cmdloop('')
    except KeyboardInterrupt:
        pass
