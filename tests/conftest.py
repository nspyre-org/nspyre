"""
pytest fixtures

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""

from pathlib import Path
import subprocess
import atexit
import time
import logging
from contextlib import contextmanager

import pytest

from nspyre import InstrumentGateway, nspyre_init_logger

HERE = Path(__file__).parent
DRIVERS = HERE / 'fixtures/drivers'

@pytest.fixture
def tmp_log_file():
    """Generate a temporary log file that can be analyzed by the test"""
    path = Path(HERE / 'tmp/test.log')
    # delete the log file if it already exists
    path.unlink(missing_ok=True)
    nspyre_init_logger(
        logging.DEBUG,
        log_path=path,
        log_path_level=logging.DEBUG
    )

    return path

@pytest.fixture
def inserv():
    """Create an instrument server"""

    # start the instrument server in a new process
    # TODO if another inserv is already running, start one on a new port
    inserv_log_path = Path(HERE / 'tmp/inserv.log')
    # delete the log file if it already exists
    inserv_log_path.unlink(missing_ok=True)
    inserv_proc = subprocess.Popen(['nspyre-inserv', '-s', '-v', 'debug', '-l', inserv_log_path],
                                stdin=subprocess.PIPE)
    # make sure the inserv gets killed on exit even if there's an error
    def cleanup():
        inserv_proc.kill()
    atexit.register(cleanup)

    # return the log path
    yield inserv_log_path

    # stop the instrument server process
    inserv_proc.kill()

# depend on tmp_log_file to make sure it gets called first
@pytest.fixture
def gateway(inserv, tmp_log_file):
    """Return a gateway connected to the instrument server"""

    # ignore logging while we attempt to connect
    logging.disable(logging.CRITICAL)
    # wait until the server is online
    counter = 0
    while True:
        try:
            with InstrumentGateway() as gw:
                # connection succeeded, so re-enable logging
                logging.disable(logging.NOTSET)

                yield gw

                break
        except:
            time.sleep(0.1)
            # wait up to 1 second before giving up
            assert counter < 10
            counter += 1

@pytest.fixture
def gateway_devs(gateway):
    """Return a gateway with initialized test devices"""

    # add test drivers to instrument server
    gateway.add('daq', DRIVERS / 'fake_daq.py', 'FakeDAQ')
    gateway.add('pel', DRIVERS / 'fake_pellicle.py', 'FakePellicle')
    gateway.add('sg', DRIVERS / 'fake_sg.py', 'FakeSigGen')
    gateway.add('vm', 'lantz.drivers.examples', 'LantzVoltmeter', import_or_file='import')

    yield gateway

    # remove drivers from instrument server
    for d in list(gateway.devs):
        gateway.remove(d)
