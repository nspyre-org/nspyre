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
import socket
from contextlib import closing

import pytest

from nspyre import InstrumentGateway, nspyre_init_logger

HERE = Path(__file__).parent
DRIVERS = HERE / 'fixtures/drivers'

def _free_port():
    """Return a free port number"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

@pytest.fixture
def free_port():
    return _free_port()

@pytest.fixture
def inserv():
    """Create an instrument server"""
    port = _free_port()
    inserv_log_path = Path(HERE / 'tmp/inserv.log')
    # delete the log file if it already exists
    inserv_log_path.unlink(missing_ok=True)
    # start the instrument server in a new process
    inserv_proc = subprocess.Popen(['nspyre-inserv', '-s', '-v', 'debug', '-l', inserv_log_path, '-p', str(port)],
                                stdin=subprocess.PIPE)
    # make sure the inserv gets killed on exit even if there's an error
    def cleanup():
        inserv_proc.kill()
    atexit.register(cleanup)

    yield {'port': port, 'log': inserv_log_path}

    # stop the instrument server process
    inserv_proc.kill()

# depend on inserv to make sure it gets started first
@pytest.fixture
def gateway(inserv):
    """Return a gateway connected to the instrument server"""

    # ignore logging while we attempt to connect
    logging.disable(logging.CRITICAL)

    # wait until the server is online
    counter = 0
    while True:
        # wait until the instrument server is online
        try:
            with InstrumentGateway(port=inserv['port']) as gw:
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
def gateway_with_devs(gateway):
    """Return a gateway with initialized test devices"""

    # add test drivers to instrument server
    gateway.add('daq', DRIVERS / 'fake_daq.py', 'FakeDAQ')
    gateway.add('pel', DRIVERS / 'fake_pellicle.py', 'FakePellicle')
    gateway.add('sg', DRIVERS / 'fake_sg.py', 'FakeSigGen')

    yield gateway

    # remove drivers from instrument server
    for d in list(gateway.devs):
        gateway.remove(d)
