import numpy as np
import time
import logging
import random

from nspyre.dataserv import DataSource, DataSink, SINK_DATA_TYPE_DEFAULT, SINK_DATA_TYPE_DELTA, SINK_DATA_TYPE_PICKLE
from nspyre.definitions import DATASERV_PORT

logger = logging.getLogger(__name__)

def test_dataserv_push_pop(name: str='push_pop', data_type_override: bytes=SINK_DATA_TYPE_DEFAULT):
    """Test the base functionality of the data server by synchronously
    pushing then popping an object repeatedly, and verifying the data integrity
    after it passes through the server"""

    source = DataSource(name, 'localhost', DATASERV_PORT)
    # allow time for the server to set up the data source
    time.sleep(0.1)

    sink = DataSink(name, 'localhost', DATASERV_PORT, data_type_override=data_type_override)
    # allow time for the server to set up the data sink
    time.sleep(0.1)

    # example data set 2D array
    # array size
    n = 100
    watched_var = np.zeros((n, n))

    iterations = 1000
    start_time = time.time()
    for i in range(iterations):
        # pick a number of changes to make to the data set
        nchanges = np.random.randint(1, 10)
        for c in range(nchanges):
            # pick a random index
            idx1 = np.random.randint(0, n-1)
            idx2 = np.random.randint(0, n-1)
            # set that index to a random value
            watched_var[idx1][idx2] = np.random.rand()

        # push the new value to the data server
        source.push(watched_var)
        # pop the new value from the data server
        remote_watched_var = sink.pop()
        # make sure they're the same
        assert watched_var.all() == remote_watched_var.all()
        logger.info(f'completed [{100*(i+1)/iterations}]%')
    end_time = time.time()

    # clean up
    source.stop()
    sink.stop()

    logger.info(f'completed in [{end_time - start_time:.3f}]s')

def test_dataserv_push_pop_delta():
    """Test the base functionality of the data server by synchronously
    pushing then popping an object repeatedly, and verifying the data integrity
    after it passes through the server - but force the server to use deltas"""
    test_dataserv_push_pop(name='push_pop_delta', data_type_override=SINK_DATA_TYPE_DELTA)

def test_dataserv_push_pop_pickle():
    """Test the base functionality of the data server by synchronously
    pushing then popping an object repeatedly, and verifying the data integrity
    after it passes through the server - but force the server to use pickles"""
    test_dataserv_push_pop(name='push_pop_pickle', data_type_override=SINK_DATA_TYPE_PICKLE)

# def test_dataserv_push_multipop():

#     # test object
#     obj_n = 5
#     obj = np.ones((obj_n, obj_n))

#     # connection to the data server that we can push objects to
#     source = DataSource('data1', 'localhost', DATASERV_PORT)

#     # wait for the data source to be connected
#     time.sleep(1)

#     # connection to the data server that we can pop objects from
#     sink1 = DataSink('data1', 'localhost', DATASERV_PORT)
#     sink2 = DataSink('data1', 'localhost', DATASERV_PORT)

#     for i in range(obj_n):
#         for j in range(obj_n):
#             # change the object
#             obj[i][j] = np.random.rand()
#             # push the change to the server
#             source.push(obj)

#             # pop the change from the server
#             tele_obj1 = sink1.pop()
#             tele_obj2 = sink2.pop()
#             # make sure the copy coming from the server is identical to the local copy
#             assert obj.all() == tele_obj1.all()
#             assert obj.all() == tele_obj2.all()

#     source.stop()
#     sink1.stop()
#     sink2.stop()

# def test_dataserv_push_late_pop():

#     # test object
#     obj_n = 5
#     obj = np.ones((obj_n, obj_n))

#     # connection to the data server that we can push objects to
#     source = DataSource('data1', 'localhost', DATASERV_PORT)

#     for i in range(obj_n):
#         source.push(obj)

#     source.stop()
