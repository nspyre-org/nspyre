"""
pytest fixtures

Author: Jacob Feder
Date: 11/12/2020
"""

###########################
# imports
###########################

# std
from pathlib import Path
import subprocess
import atexit
import time
import logging

# 3rd party
import pytest
import psutil

# nspyre
from nspyre.inserv.gateway import InservGateway

###########################
# globals
###########################

server_cfg_path = Path(__file__).parent / Path('fixtures/configs/server_test_config.yaml')
client_cfg_path = Path(__file__).parent / Path('fixtures/configs/client_test_config.yaml')

###########################
# fixtures
###########################

@pytest.fixture()
def client_config_path():
    """return the client config path"""
    logging.info('getting client config')
    return client_cfg_path.resolve()

@pytest.fixture(scope='class')
def gateway():
    """return an instrument gateway"""
    logging.info('getting gateway')
    with InservGateway(client_cfg_path) as insgw:
        yield insgw

@pytest.fixture(scope='session', autouse=True)
def setup():
    """start mongodb and the instrument server in subprocesses for use by 
    subsequent tests"""
    logging.info('test setup...')

    # search through all running processes, and only start mongo if it's not
    # already running, since it takes awhile to start up
    if not 'mongod' in [p.name() for p in psutil.process_iter()]:
        logging.info('running nspyre-mongodb')
        # start mongod in a subprocess
        mongo = subprocess.run(['nspyre-mongodb'])
        # give time for the database to start
        time.sleep(30)

    # start the instrument server
    inserv = subprocess.Popen(['nspyre-inserv', '-c', server_cfg_path, '-v', 'debug'],
                                stdin=subprocess.PIPE)

    # make sure the inserv gets killed on exit even if there's an error
    def cleanup():
        inserv.kill()
    atexit.register(cleanup)

    # ignore logging while we attempt to connect
    logging.disable(logging.CRITICAL)
    # wait until the server is online
    while True:
        try:
            with InservGateway(client_cfg_path) as insgw:
                getattr(insgw, 'tserv')
                break
        except:
            time.sleep(0.1)
    # re-enable logging
    logging.disable(logging.NOTSET)

    # now the tests run
    yield

    logging.info('test teardown')
