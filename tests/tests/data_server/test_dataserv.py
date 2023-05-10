import logging
import time

import numpy as np
from nspyre import DataSink
from nspyre import DataSource

logger = logging.getLogger(__name__)


NPUSHES = 100


def test_dataserv_push_pop():
    """Test the base functionality of the data server by synchronously
    pushing then popping an object repeatedly."""
    name = 'push_pop'
    with DataSource(name) as source, DataSink(name) as sink:
        # example data set 2D array
        # array size
        n = 1000
        watched_var = np.zeros((n, n))

        total_time = 0.0
        for i in range(NPUSHES):
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
            source.push({'watched_var': watched_var})
            # wait for the new data to be available from the data server
            sink.pop()
            end_time = time.time()
            total_time += end_time - start_time
            # make sure the data is identical
            assert watched_var.all() == sink.watched_var.all()
            logger.info(f'Completed [{100*(i+1)/NPUSHES:>5.1f}]%.')
        avg_time = total_time / NPUSHES

    logger.info(
        f'Completed run [{name}] - total time [{total_time:.3f}]s average time per '
        f'push/pop [{avg_time:.3f}]s.'
    )


def test_dataserv_push_multipop(name: str = 'push_multipop'):
    """Test the base functionality of the data server by synchronously
    pushing an object, then popping it from two different sinks"""
    name = 'push_multipop'
    with DataSource(name) as source, DataSink(name) as sink1, DataSink(name) as sink2:
        # example data set 2D array
        # array size
        n = 1000
        watched_var = np.zeros((n, n))

        total_time = 0.0
        for i in range(NPUSHES):
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
            source.push({'watched_var': watched_var})
            # wait for the new data to be available from the data server
            sink1.pop()
            sink2.pop()
            end_time = time.time()
            total_time += end_time - start_time
            # make sure the data is identical
            assert watched_var.all() == sink1.watched_var.all()
            assert watched_var.all() == sink2.watched_var.all()
            logger.info(f'Completed [{100*(i+1)/NPUSHES:>5.1f}]%.')
        avg_time = total_time / NPUSHES

    logger.info(
        f'Completed run [{name}] - total time [{total_time:.3f}]s average time per '
        f'push/pop [{avg_time:.3f}]s.'
    )


def test_dataserv_push_no_pop(dataserv):
    """Test pushing objects but not popping them"""

    n = 5
    obj = np.ones((n, n))

    nconnects = 3
    for i in range(nconnects):
        # connect to the data server
        with DataSource('push_no_pop') as source:
            for _ in range(NPUSHES):
                source.push(obj)
        time.sleep(0.1)

        # make sure the DataSource event loop closed properly
        assert not source._thread.is_alive()

        logger.info(f'Completed [{100*(i+1)/nconnects:>5.1f}]%.')
