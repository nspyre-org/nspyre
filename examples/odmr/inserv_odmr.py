#!/usr/bin/env python
"""
Start up an instrument server and load drivers for ODMR experiments.

Author: Jacob Feder
Date: 12/27/2021
"""
import logging
import signal
from pathlib import Path

from nspyre import InservCmdPrompt
from nspyre import InstrumentServer
from nspyre import nspyre_init_logger

HERE = Path(__file__).parent


def init_inserv():
    """Create and return a running instrument server."""

    # create a new instrument server
    inserv = InstrumentServer()

    # properly stop the server if a kill signal is received
    def stop_server(signum, frame):
        inserv.stop()
        raise SystemExit

    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)

    # start the server
    inserv.start()

    return inserv


def init_odmr_instruments(inserv):
    """Add the instruments required for an ODMR experiment to the instrument server."""
    # signal generator
    inserv.add('sg', HERE / 'drivers' / 'sg.py', 'SigGen')
    # data acquisition instrument
    inserv.add('daq', HERE / 'drivers' / 'daq.py', 'DAQ')


if __name__ == '__main__':
    # enable logging
    nspyre_init_logger(logging.INFO)

    # create the instrument server
    inserv = init_inserv()

    # add necessary instruments to the server
    init_odmr_instruments(inserv)

    # run a CLI (command-line interface) that allows the user to enter
    # commands to control the server
    cmd_prompt = InservCmdPrompt(inserv)
    cmd_prompt.prompt = 'inserv > '
    cmd_prompt.cmdloop('')
