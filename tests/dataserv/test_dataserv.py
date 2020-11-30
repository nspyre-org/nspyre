import numpy as np
import time

from nspyre.dataserv import DataSource, DataSink
from nspyre.definitions import DATASERV_PORT

# def test_dataserv_push_pop():

#     # test object
#     obj_n = 5
#     obj = np.ones((obj_n, obj_n))

#     # connection to the data server that we can push objects to
#     source = DataSource('data1', 'localhost', DATASERV_PORT)

#     # wait for the data source to be connected
#     time.sleep(1)

#     # connection to the data server that we can pop objects from
#     sink1 = DataSink('data1', 'localhost', DATASERV_PORT)

#     for i in range(obj_n):
#         for j in range(obj_n):
#             # change the object
#             obj[i][j] = np.random.rand()
#             # push the change to the server
#             source.push(obj)
#             # pull the change from the server
#             tele_obj = sink1.pop()
#             # make sure the copy coming from the server is identical to the local copy
#             assert obj.all() == tele_obj.all()

#     source.stop()
#     sink1.stop()

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

#             # pull the change from the server
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

def test_dataserv_kill():

    source = DataSource('data1', 'localhost', DATASERV_PORT)

    time.sleep(1)

    sink1 = DataSink('data1', 'localhost', DATASERV_PORT)
    print('abc1')
    time.sleep(1)

    source.stop()
    # sink1.stop()

if __name__ == '__main__':
    from nspyre.misc.logging import nspyre_init_logger
    import logging
    nspyre_init_logger(logging.DEBUG)
    test_dataserv_kill()