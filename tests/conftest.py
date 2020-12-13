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
from nspyre.definitions import DATASERV_PORT
from nspyre.dataserv import DataSource

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
    """start mongodb and the instrument server in subprocesses for use by subsequent tests"""

    logging.info('test setup...')

    # list of the names of currently running processes so that we can
    # only start our own instances if they're not already running
    processes = [p.name() for p in psutil.process_iter()]

    processes_to_kill = []

    if not 'mongod' in processes:
        logging.info('running nspyre-mongodb')
        # start mongod in a subprocess and wait for it to start
        mongo = subprocess.run(['nspyre-mongodb'])
        processes_to_kill.append(mongo)

    if not 'nspyre-inserv' in processes:
        # start the instrument server
        inserv = subprocess.Popen(['nspyre-inserv', '-c', server_cfg_path, '-v', 'debug'],
                                    stdin=subprocess.PIPE)
        processes_to_kill.append(inserv)

    if not 'nspyre-dataserv' in processes:
        # TODO start the data server
        # for some reason starting the dataserv from pytest breaks
        # the ProcessPoolExecutor and hangs the xdelta3 call in the dataserv
        # (tested only on debian)
        # dataserv = subprocess.Popen(['nspyre-dataserv', '-v', 'debug'],
        #                             stdin=subprocess.PIPE)
        # processes_to_kill.append(dataserv)
        pass

    # make sure the processes get killed on exit even if there's an error
    def cleanup():
        for p in processes_to_kill:
            p.kill()
    atexit.register(cleanup)

    # ignore logging while we attempt to connect
    logging.disable(logging.CRITICAL)
    while True:
        # wait until the instrument server is online
        try:
            with InservGateway(client_cfg_path) as insgw:
                getattr(insgw, 'tserv')
                break
        except:
            time.sleep(0.1)
        # wait until the data server is online
        # TODO
        # source = DataSource('test', 'localhost', DATASERV_PORT)
        # source.wait_connected()
        # source.stop()
    # re-enable logging
    logging.disable(logging.NOTSET)

    # now the tests run
    yield

    logging.info('tests completed')
