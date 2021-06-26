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
import importlib
import inspect
import sys

import pytest

from nspyre import InstrumentGateway

HERE = Path(__file__).parent

@pytest.fixture(scope='class')
def gateway():
    """return an instrument gateway"""
    logging.info('getting gateway')

    drivers_path = HERE / 'fixtures/drivers'
    with InstrumentGateway() as gw:
        # add test drivers to instrument server
        gw.add('daq', drivers_path / 'fake_daq.py', 'FakeDAQ')
        gw.add('pel', drivers_path / 'fake_pellicle.py', 'FakePellicle')
        gw.add('sg', drivers_path / 'fake_sg.py', 'FakeSigGen')
        # now the tests run
        yield gw
        # remove drivers from instrument server
        for d in list(gw.devs):
            gw.remove(d)

@pytest.fixture(scope='session', autouse=True)
def setup():
    """start the instrument server in a subprocess for use by subsequent tests"""
    logging.info('test setup...')

    # start the instrument server
    inserv = subprocess.Popen(['nspyre-inserv', '-s', '-v', 'debug'],
                                stdin=subprocess.PIPE)
    # make sure the inserv gets killed on exit even if there's an error
    def cleanup():
        inserv.kill()
    atexit.register(cleanup)

    # ignore logging while we attempt to connect
    logging.disable(logging.CRITICAL)
    # wait until the server is online
    counter = 0
    while True:
        try:
            with InstrumentGateway() as insgw:
                getattr(insgw, 'devs')
                break
        except:
            time.sleep(0.1)
            assert counter < 10
            counter += 1
    # re-enable logging
    logging.disable(logging.NOTSET)

    # now the tests run
    yield

    logging.info('tests completed')
