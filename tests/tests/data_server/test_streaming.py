import logging
import time

import numpy as np
from nspyre import DataSink
from nspyre import DataSource
from nspyre.data_server.streaming_list import StreamingList
from nspyre.misc.misc import _total_sizeof

logger = logging.getLogger(__name__)

NPUSHES = 100

def test_dataserv_streaming_list():
    sl1 = StreamingList(['a', 'b', 'c'])
    sl2 = StreamingList(['e', 'f', 'g'])
    assert sl1 == ['a', 'b', 'c']
    assert sl1.diff_ops == [('i', 0, 'a'), ('i', 1, 'b'), ('i', 2, 'c')]
    assert sl2 == ['e', 'f', 'g']
    assert sl2.diff_ops == [('i', 0, 'e'), ('i', 1, 'f'), ('i', 2, 'g')]
    sl1.append('d')
    assert sl1 == ['a', 'b', 'c', 'd']
    assert sl1.diff_ops == [('i', 0, 'a'), ('i', 1, 'b'), ('i', 2, 'c'), ('i', 3, 'd')]
    sl1.extend(sl2)
    assert sl1 == ['a', 'b', 'c', 'd', 'e', 'f', 'g']
    assert sl1.diff_ops == [
        ('i', 0, 'a'),
        ('i', 1, 'b'),
        ('i', 2, 'c'),
        ('i', 3, 'd'),
        ('i', 4, 'e'),
        ('i', 5, 'f'),
        ('i', 6, 'g'),
    ]
    sl1[0] = 'x'
    assert sl1 == ['x', 'b', 'c', 'd', 'e', 'f', 'g']
    assert sl1.diff_ops == [
        ('i', 0, 'a'),
        ('i', 1, 'b'),
        ('i', 2, 'c'),
        ('i', 3, 'd'),
        ('i', 4, 'e'),
        ('i', 5, 'f'),
        ('i', 6, 'g'),
        ('u', 0, 'x'),
    ]
    sl1[0:2] = ['y', 'z']
    assert sl1 == ['y', 'z', 'c', 'd', 'e', 'f', 'g']
    assert sl1.diff_ops == [
        ('i', 0, 'a'),
        ('i', 1, 'b'),
        ('i', 2, 'c'),
        ('i', 3, 'd'),
        ('i', 4, 'e'),
        ('i', 5, 'f'),
        ('i', 6, 'g'),
        ('u', 0, 'x'),
        ('u', slice(0, 2), ['y', 'z']),
    ]
    sl1._clear_diff_ops()
    assert sl1 == ['y', 'z', 'c', 'd', 'e', 'f', 'g']
    assert sl1.diff_ops == []
    sl3 = sl1 + ['h', 'i']
    assert sl3 == ['y', 'z', 'c', 'd', 'e', 'f', 'g', 'h', 'i']
    assert sl3.diff_ops == [
        ('i', 0, 'y'),
        ('i', 1, 'z'),
        ('i', 2, 'c'),
        ('i', 3, 'd'),
        ('i', 4, 'e'),
        ('i', 5, 'f'),
        ('i', 6, 'g'),
        ('i', 7, 'h'),
        ('i', 8, 'i'),
    ]
    sl3.remove('h')
    assert sl3 == ['y', 'z', 'c', 'd', 'e', 'f', 'g', 'i']
    assert sl3.diff_ops == [
        ('i', 0, 'y'),
        ('i', 1, 'z'),
        ('i', 2, 'c'),
        ('i', 3, 'd'),
        ('i', 4, 'e'),
        ('i', 5, 'f'),
        ('i', 6, 'g'),
        ('i', 7, 'h'),
        ('i', 8, 'i'),
        ('d', 7),
    ]
    sl4 = StreamingList([1, 2]) * 3
    assert sl4 == [1, 2, 1, 2, 1, 2]
    assert sl4.diff_ops == [
        ('i', 0, 1),
        ('i', 1, 2),
        ('i', 2, 1),
        ('i', 3, 2),
        ('i', 4, 1),
        ('i', 5, 2),
    ]
    sl4.pop(0)
    sl4.pop(1)
    assert sl4 == [2, 2, 1, 2]
    assert sl4.diff_ops == [
        ('i', 0, 1),
        ('i', 1, 2),
        ('i', 2, 1),
        ('i', 3, 2),
        ('i', 4, 1),
        ('i', 5, 2),
        ('d', 0),
        ('d', 1),
    ]
    sl4._clear_diff_ops()
    sl4._merge([('d', 0), ('i', 0, 3)])
    assert sl4 == [3, 2, 1, 2]
    sl4._merge([('d', 1), ('u', 2, 'a')])
    assert sl4 == [3, 1, 'a']


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
    logger.info(f'transferred [{_total_sizeof(sink.data)/1e9:.3f}] GB.')
    logger.info(
        f'completed run [{name}] - total time [{total_time:.3f}]s average time per push/pop [{avg_time:.3f}]s'
    )
