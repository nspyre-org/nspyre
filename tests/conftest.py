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
    return client_cfg_path

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
    # already running, since it takes awhile to startup
    if not 'mongod' in [p.name() for p in psutil.process_iter()]:
        logging.info('running nspyre-mongodb')
        # start mongod in a subprocess
        mongo = subprocess.run(['nspyre-mongodb'])
        # give time for the database to start
        time.sleep(30)

    # start the server
    inserv = subprocess.Popen(['python',
                    str(Path(__file__).parent / Path('fixtures/inserv_proc.py')),
                    server_cfg_path])
    
    # make sure the inserv gets killed on exit even if there's an error
    def cleanup():
        inserv.kill()
    atexit.register(cleanup)

    # wait until the server is online
    # ignore log warnings while we attempt to connect
    logger = logging.getLogger()
    logger.disabled = True
    while True:
        try:
            with InservGateway(client_cfg_path) as insgw:
                getattr(insgw, 'tserv')
                break
        except:
            time.sleep(0.1)
    logger.disabled = False

    # now the tests run
    yield

    logging.info('test teardown')
