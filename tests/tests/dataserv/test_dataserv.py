import numpy as np
import time
import logging

from nspyre import (
    DataSource,
    DataSink,
    SINK_DATA_TYPE_DEFAULT,
    SINK_DATA_TYPE_DELTA,
    SINK_DATA_TYPE_PICKLE,
)

logger = logging.getLogger(__name__)


def dataserv_push_pop(
    name: str = 'push_pop', data_type_override: bytes = SINK_DATA_TYPE_DEFAULT
):
    """Test the base functionality of the data server by synchronously
    pushing then popping an object repeatedly"""

    with DataSource(name) as source:
        # allow time for the server to set up the data source
        time.sleep(0.1)
        with DataSink(name, data_type_override=data_type_override) as sink:
            # allow time for the server to set up the data sink
            time.sleep(0.1)

            # example data set 2D array
            # array size
            n = 1000
            watched_var = np.zeros((n, n))
            source.add('watched_var', watched_var)

            iterations = 100
            total_time = 0.0
            for i in range(iterations):
                # pick a number of changes to make to the data set
                nchanges = np.random.randint(1, 10)
                for _ in range(nchanges):
                    # pick a random index
                    idx1 = np.random.randint(0, n - 1)
                    idx2 = np.random.randint(0, n - 1)
                    # set that index to a random value
                    watched_var[idx1][idx2] = np.random.rand()

                # time the data server operations
                start_time = time.time()
                # push the new value to the data server
                source.update()
                # wait for the new data to be available from the data server
                sink.update()
                end_time = time.time()
                total_time += end_time - start_time
                # make sure the data is identical
                assert watched_var.all() == sink.watched_var.all()
                logger.info(f'completed [{100*(i+1)/iterations:>5.1f}]%')
            avg_time = total_time / iterations

    logger.info(
        f'completed run [{name}] - total time [{total_time:.3f}]s average time per push/pop [{avg_time:.3f}]s'
    )


def test_dataserv_push_pop_delta(dataserv):
    """Test the base functionality of the data server by synchronously
    pushing then popping an object repeatedly, but force the server to use
    deltas"""
    dataserv_push_pop(name='push_pop_delta', data_type_override=SINK_DATA_TYPE_DELTA)


def test_dataserv_push_pop_pickle(dataserv):
    """Test the base functionality of the data server by synchronously
    pushing then popping an object repeatedly, but force the server to use
    pickles"""
    dataserv_push_pop(name='push_pop_pickle', data_type_override=SINK_DATA_TYPE_PICKLE)


def dataserv_push_multipop(
    name: str = 'push_multipop',
    data_type_override: bytes = SINK_DATA_TYPE_DEFAULT,
):
    """Test the base functionality of the data server by synchronously
    pushing an object, then popping it from two different sinks"""

    with DataSource(name) as source:
        # allow time for the server to set up the data source
        time.sleep(0.1)
        with DataSink(name, data_type_override=data_type_override) as sink1, DataSink(
            name, data_type_override=data_type_override
        ) as sink2:
            # allow time for the server to set up the data sink
            time.sleep(0.1)

            # example data set 2D array
            # array size
            n = 1000
            watched_var = np.zeros((n, n))
            source.add('watched_var', watched_var)

            iterations = 100
            total_time = 0.0
            for i in range(iterations):
                # pick a number of changes to make to the data set
                nchanges = np.random.randint(1, 10)
                for _ in range(nchanges):
                    # pick a random index
                    idx1 = np.random.randint(0, n - 1)
                    idx2 = np.random.randint(0, n - 1)
                    # set that index to a random value
                    watched_var[idx1][idx2] = np.random.rand()

                # time the data server operations
                start_time = time.time()
                # push the new value to the data server
                source.update()
                # wait for the new data to be available from the data server
                sink1.update()
                sink2.update()
                end_time = time.time()
                total_time += end_time - start_time
                # make sure the data is identical
                assert watched_var.all() == sink1.watched_var.all()
                assert watched_var.all() == sink2.watched_var.all()
                logger.info(f'completed [{100*(i+1)/iterations:>5.1f}]%')
            avg_time = total_time / iterations

    logger.info(
        f'completed run [{name}] - total time [{total_time:.3f}]s average time per push/pop [{avg_time:.3f}]s'
    )


def test_dataserv_push_multipop_delta(dataserv):
    """Test the base functionality of the data server by synchronously
    pushing an object, then popping it from two different sinks, but force the
    server to use deltas"""
    dataserv_push_multipop(
        name='push_pop_delta', data_type_override=SINK_DATA_TYPE_DELTA
    )


def test_dataserv_push_multipop_pickle(dataserv):
    """Test the base functionality of the data server by synchronously
    pushing an object, then popping it from two different sinks, but force the
    server to use pickles"""
    dataserv_push_multipop(
        name='push_pop_pickle', data_type_override=SINK_DATA_TYPE_PICKLE
    )


# def test_dataserv_push_late_pop():

#     # test object
#     obj_n = 5
#     obj = np.ones((obj_n, obj_n))

#     # connection to the data server that we can push objects to
#     source = DataSource('data1', 'localhost', DATASERV_PORT)

#     for i in range(obj_n):
#         source.push(obj)

#     source.stop()
