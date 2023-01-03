import logging
import time

import numpy as np
from nspyre import DataSink
from nspyre import DataSource
from nspyre.data_server.streaming_list import StreamingList
from nspyre.misc.misc import total_sizeof

logger = logging.getLogger(__name__)

NPUSHES = 100


def test_dataserv_streaming_push_pop():
    name = 'streaming_push_pop'
    with DataSource(name) as source, DataSink(name) as sink:
        # disregard the first pop since the source hasn't provided any data yet
        sink.pop()
        sl1 = StreamingList([])
        sl2 = StreamingList([1, 2])
        watched_var = {'sl1': sl1, 'other': 'test', 'sl2': sl2}
        total_time = 0.0
        for i in range(NPUSHES):
            rand = np.random.randint(1000)
            watched_var['sl1'].append(rand)
            watched_var['sl2'].append(i + 5)
            start_time = time.time()
            source.push(watched_var)
            sink.pop()
            # logger.error(f'sinky{sink.streaming_obj_db}')
            end_time = time.time()
            total_time += end_time - start_time
            # make sure the data is identical
            assert watched_var == sink.data
            logger.info(f'completed [{100*(i+1)/NPUSHES:>5.1f}]%')
        avg_time = total_time / NPUSHES

    logger.info(
        f'completed run [{name}] - total time [{total_time:.3f}]s average time per push/pop [{avg_time:.3f}]s'
    )


def test_dataserv_streaming_push_pop_big():
    name = 'streaming_push_pop_big'
    with DataSource(name) as source, DataSink(name) as sink:
        # disregard the first pop since the source hasn't provided any data yet
        sink.pop()
        sl1 = StreamingList([])
        total_time = 0.0
        for i in range(NPUSHES):
            sl1.append(np.random.rand(1000, 1000))
            start_time = time.time()
            source.push(sl1)
            sink.pop()
            end_time = time.time()
            total_time += end_time - start_time
            # make sure the data is identical
            for i in range(len(sl1)):
                assert sl1[i].all() == sink.data[i].all()
            logger.info(f'completed [{100*(i+1)/NPUSHES:>5.1f}]%')
        avg_time = total_time / NPUSHES
    logger.info(f'transferred [{total_sizeof(sink.data)/1e9:.3f}] GB.')
    logger.info(
        f'completed run [{name}] - total time [{total_time:.3f}]s average time per push/pop [{avg_time:.3f}]s'
    )
