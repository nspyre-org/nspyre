"""
pytest fixtures

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
import socket
import subprocess
import time
from contextlib import closing
from pathlib import Path

import pytest
from nspyre import InstrumentGateway
from nspyre import InstrumentGatewayError
from nspyre import InstrumentServer

HERE = Path(__file__).parent
DRIVERS = HERE / 'fixtures' / 'drivers'


def _free_port():
    """Return a free port number."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@pytest.fixture
def free_port():
    return _free_port()


@pytest.fixture
def dataserv():
    """Start a data server if one isn't running."""

    process = subprocess.Popen(['nspyre-dataserv'])
    time.sleep(1)

    yield process

    process.kill()
    time.sleep(1)


@pytest.fixture
def inserv():
    """Create an instrument server."""
    port = _free_port()

    inserv = InstrumentServer(port=port)
    inserv.start()

    yield inserv

    # stop the instrument server
    inserv.stop()


# depend on inserv to make sure it gets started first
@pytest.fixture
def gateway(inserv):
    """Return a gateway connected to the instrument server."""

    # ignore logging while we attempt to connect
    logging.disable(logging.CRITICAL)

    # wait until the server is online
    counter = 0
    while True:
        # wait until the instrument server is online
        try:
            with InstrumentGateway(port=inserv._port) as gw:
                # connection succeeded, so re-enable logging
                logging.disable(logging.NOTSET)

                yield gw

                break
        except InstrumentGatewayError:
            time.sleep(0.1)
            # wait up to 1 second before giving up
            assert counter < 10
            counter += 1


@pytest.fixture
def gateway_with_devs(gateway):
    """Return a gateway with initialized test devices."""

    # add test drivers to instrument server
    gateway.add('daq', DRIVERS / 'fake_daq.py', 'FakeDAQ')
    gateway.add('pel', DRIVERS / 'fake_pellicle.py', 'FakePellicle')
    gateway.add('sg', DRIVERS / 'fake_sg.py', 'FakeSigGen')

    yield gateway

    # remove drivers from instrument server
    for d in list(gateway._devs):
        gateway.remove(d)
