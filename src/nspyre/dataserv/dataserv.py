"""
The nspyre DataServer transports arbitrary python objects over a TCP/IP socket to a set of local or remote network clients, and keeps those objects up to date as they are modified. For each data set on the data server, there is a single data "source", and a set of data "sinks".

Objects are serialized by the source then pushed to the server. For local clients, the data server sends the serialized data directly to the be deserialized by the sink process. For remote clients, the serialized object data is diffed with any previously pushed data and the diff is sent rather than the full object in order to minimize the required network bandwidth. The client can then reconstruct the pushed data using a local copy of the last version of the object, and the diff received from the server.

Example usage:

# run the command-line tool for starting up the data server, specifying the port
nspyre-dataserv -p 12345

----------------------------------

# data "source" code
# running on the same machine as the data server, in the same or a different
# process

from nspyre import DataSource
import numpy as np

# connect to the data server and create a data set, or connect to an
# existing one with the same name if it was created earlier
source = DataSource('my_dataset', 12345)

# do an experiment where we measure voltage of something as a function of frequency
n = 100
frequencies = np.linspace(1e6, 100e6, n)
voltages = np.zeros(n)

# add objects to the data set
source.add('freq', x)
source.add('volts', y)

for f in frequencies:
    some_instrument.set_frequency(f)
    voltages[i] = other_instrument.get_voltage()
    source.update()

----------------------------------

# data "sink" code
# running on the same or a different machine as the source / data server

from nspyre import DataSink

# connect the data set on the data server
sink = DataSink('my_dataset', '192.168.1.50', 12345)

while True:
    # block until an updated version of the data set is available
    sink.update()
    # sink.freq and sink.volts have been modified
    # replot the data to show the new values
    my_plot_update(sink.freq, sink.volts)

Author: Jacob Feder
Date: 11/29/2020
"""

import asyncio
import socket
from threading import Thread
import logging
import pickle
import concurrent.futures
import xdelta3
from typing import Dict, Any

logger = logging.getLogger(__name__)

# default port to host the data server on
DATASERV_PORT = 30000

# if no data is available, any socket sender should send an empty message with an
# interval given by KEEPALIVE_TIMEOUT (s)
KEEPALIVE_TIMEOUT = 3
# time (s) that the sender has to do work before it should give up
# in order to prevent a timeout on its associated receiver
OPS_TIMEOUT = 10
# timeout (s) for receive connections
TIMEOUT = (KEEPALIVE_TIMEOUT + OPS_TIMEOUT) + 1

# maximum size of the data queue
QUEUE_SIZE = 5

# indicates that the client is requesting some data about the server
NEGOTIATION_INFO = b'\xDE'
# TODO
# NEGOTIATION_CMD = b'\xAD'
# indicates that the client will source data to the server
NEGOTIATION_SOURCE = b'\xBE'
# indicates that the client will sink data from the server
NEGOTIATION_SINK = b'\xEF'
# timeout (s) for send/recv operations during the client negotiation phase
NEGOTIATION_TIMEOUT = TIMEOUT

# timeout for relatively quick operations
FAST_TIMEOUT = 1.0

# custom recv_msg() and send_msg() use the following packet structure
# |                      HEADER                             | PAYLOAD
# | message length (excluding header) |      meta-data      | message
# |        HEADER_MSG_LEN             | HEADER_METADATA_LEN | variable length

# length (bytes) of the header section that identifies how large the payload is
HEADER_MSG_LEN = 8
# length (bytes) of the header section that carries meta-data
HEADER_METADATA_LEN = 8

# indicates that the data is a delta
SINK_DATA_TYPE_DELTA_UNPADDED = b'\xAB'
SINK_DATA_TYPE_DELTA = SINK_DATA_TYPE_DELTA_UNPADDED + b'\x00' * (
    HEADER_METADATA_LEN - len(SINK_DATA_TYPE_DELTA_UNPADDED)
)
# indicates that the data is a raw pickle
SINK_DATA_TYPE_PICKLE_UNPADDED = b'\xCD'
SINK_DATA_TYPE_PICKLE = SINK_DATA_TYPE_PICKLE_UNPADDED + b'\x00' * (
    HEADER_METADATA_LEN - len(SINK_DATA_TYPE_PICKLE_UNPADDED)
)
# indicates that the server will decide the data type
SINK_DATA_TYPE_DEFAULT_UNPADDED = b'\xCD'
SINK_DATA_TYPE_DEFAULT = SINK_DATA_TYPE_DEFAULT_UNPADDED + b'\x00' * (
    HEADER_METADATA_LEN - len(SINK_DATA_TYPE_DEFAULT_UNPADDED)
)


class DataServerError(Exception):
    """Raised for failures with the data server"""


class CustomSock:
    """Tiny socket wrapper class that implements a custom messaging protocol"""

    def __init__(self, sock_reader, sock_writer):
        self.sock_reader = sock_reader
        self.sock_writer = sock_writer
        # (ip addr, port) of the client
        self.addr = sock_writer.get_extra_info('peername')

    async def recv_msg(self) -> tuple:
        """Receive a message through a socket by decoding the header then reading
        the rest of the message"""

        # the header bytes we receive from the client should identify
        # the length of the message payload
        msg_len_bytes = await self.sock_reader.readexactly(HEADER_MSG_LEN)
        msg_len = int.from_bytes(msg_len_bytes, byteorder='little')

        # get the metadata
        meta_data = await self.sock_reader.readexactly(HEADER_METADATA_LEN)

        # get the payload
        msg = await self.sock_reader.readexactly(msg_len)

        logger.debug(f'received [{msg_len}] bytes from [{self.addr}]')

        return (msg, meta_data)

    async def send_msg(
        self, msg: bytes, meta_data: bytes = b'\x00' * HEADER_METADATA_LEN
    ):
        """Send a byte message through a socket interface by encoding the header
        then sending the rest of the message"""

        assert len(meta_data) == HEADER_METADATA_LEN

        # calculate the payload length and package it into bytes
        msg_len_bytes = len(msg).to_bytes(HEADER_MSG_LEN, byteorder='little')

        # send the header + payload
        self.sock_writer.write(msg_len_bytes + meta_data + msg)
        await self.sock_writer.drain()

        logger.debug(f'sent [{len(msg)}] bytes to {self.addr}')

    async def close(self):
        """Fully close a socket connection"""
        self.sock_writer.close()
        await self.sock_writer.wait_closed()
        logger.debug(f'closed socket [{self.addr}]')


def queue_flush_and_put(queue, item):
    """Empty an asyncio queue then put a single item onto it"""
    for _ in range(queue.qsize()):
        queue.get_nowait()
        queue.task_done()
    queue.put_nowait(item)


def cleanup_event_loop(loop):
    """End all tasks in an event loop and exit"""
    pending_tasks = asyncio.all_tasks(loop=loop)
    # cancel each pending task
    for task in pending_tasks:
        task.cancel()
    # wait for all tasks to exit (and suppress any errors with return_exceptions=True)
    grouped_pending_tasks = asyncio.gather(
        *pending_tasks, loop=loop, return_exceptions=True
    )
    loop.run_until_complete(grouped_pending_tasks)
    loop.run_until_complete(loop.shutdown_asyncgens())
    # shut down the event loop
    loop.close()


class DataSet:
    """Class that wraps a pipeline consisting of a data source and a list of data sinks"""

    def __init__(self):
        # dict of the form
        # {'task': asyncio task object for source,
        # 'sock': socket for the source}
        self.source = None
        # dict of dicts of the form
        # {('127.0.0.1', 13445):
        #           {'task': asyncio task object for sink,
        #           'sock': socket for the sink,
        #           'queue': sink FIFO/queue},
        # ('192.168.1.5', 19859): ... }
        self.sinks = {}

    async def run_sink(
        self,
        event_loop: asyncio.AbstractEventLoop,
        sock: CustomSock,
        data_type_override: bytes,
    ):
        """run a new data sink until it closes
        sock: socket for the sink
        data_type_override: SINK_DATA_TYPE_DEFAULT for the server to decide whether diffs should be performed
                            SINK_DATA_TYPE_PICKLE to always use pickle data (no diff)
                            SINK_DATA_TYPE_DELTA to always generate a diff"""
        sink_id = sock.addr
        # sink connections should get unique ports, so this shouldn't happen
        assert sink_id not in self.sinks
        # create the sink task
        task = asyncio.create_task(
            self._sink_coro(event_loop, sink_id, data_type_override=data_type_override)
        )
        # add the sink data to the DataSet
        sink_dict = {
            'task': task,
            'sock': sock,
            'queue': asyncio.Queue(maxsize=QUEUE_SIZE),
        }
        self.sinks[sink_id] = sink_dict
        await task

    async def run_source(self, sock: CustomSock):
        """run a data source until it closes"""
        task = asyncio.create_task(self._source_coro())
        self.source = {'task': task, 'sock': sock}
        await task

    async def _source_coro(self):
        """Receive data from a source client and transfer it to the client queues"""
        sock = self.source['sock']
        try:
            while True:
                try:
                    new_pickle, _ = await asyncio.wait_for(
                        sock.recv_msg(), timeout=TIMEOUT
                    )
                except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                    # if there was a timeout / problem receiving the message
                    # the source client is dead and will be terminated
                    logger.info(
                        f'source [{sock.addr}] disconnected or hasn\'t sent a keepalive message - dropping connection'
                    )
                    raise asyncio.CancelledError

                if len(new_pickle):
                    logger.debug(
                        f'source [{sock.addr}] received pickle of [{len(new_pickle)}] bytes'
                    )
                    for sink_id in self.sinks:
                        sink = self.sinks[sink_id]
                        queue = sink['queue']
                        try:
                            queue.put_nowait(new_pickle)
                        except asyncio.QueueFull:
                            # the sink isn't consuming data fast enough
                            # so we will empty the queue and place only this most recent
                            # piece of data on it
                            logger.debug(
                                f'sink [{sink["sock"].addr}] can\'t keep up with data source'
                            )
                            # empty the queue then put a single item into it
                            queue_flush_and_put(queue, new_pickle)
                        logger.debug(
                            f'source [{sock.addr}] queued pickle of [{len(new_pickle)}] for sink [{sink["sock"].addr}]'
                        )
                else:
                    # the server just sent a keepalive signal
                    logger.debug(f'source [{sock.addr}] received keepalive')
        except asyncio.CancelledError:
            raise
        finally:
            logger.info(f'dropped source [{sock.addr}]')
            self.source = None

    async def _sink_coro(
        self,
        event_loop: asyncio.AbstractEventLoop,
        sink_id: tuple,
        data_type_override: bytes,
    ):
        """Receive source data from the queue"""
        sock = self.sinks[sink_id]['sock']
        queue = self.sinks[sink_id]['queue']
        last_pickle = None
        try:
            while True:
                try:
                    # get pickle data from the queue
                    new_pickle = await asyncio.wait_for(
                        queue.get(), timeout=KEEPALIVE_TIMEOUT
                    )
                    queue.task_done()
                    logger.debug(
                        f'sink [{sock.addr}] got [{len(new_pickle)}] bytes from queue'
                    )
                except asyncio.TimeoutError:
                    # if there's no data available, send a keepalive message
                    logger.debug(
                        f'sink [{sock.addr}] no data available - sending keepalive'
                    )
                    new_pickle = b''

                data_to_send = new_pickle
                if new_pickle:
                    if last_pickle and (
                        data_type_override == SINK_DATA_TYPE_DELTA
                        or (
                            data_type_override == SINK_DATA_TYPE_DEFAULT
                            and sock.addr[0] != '127.0.0.1'
                        )
                    ):
                        # create a new process for running the xdelta algorithm and await it
                        with concurrent.futures.ProcessPoolExecutor(
                            max_workers=1
                        ) as executor:
                            # TODO if there are many remote clients, they will be potentially duplicating work by all diff'ing the same
                            # pickles - this could be resolved by using memoization to store recently calculated diffs
                            logger.debug(
                                f'sink [{sock.addr}] calculating delta of [{len(new_pickle)}] bytes'
                            )
                            try:
                                delta_future = event_loop.run_in_executor(
                                    executor,
                                    xdelta3.encode,
                                    last_pickle,
                                    new_pickle,
                                )  # TODO fast/no compression? xdelta3.Flags.COMPLEVEL_1
                                delta = await asyncio.wait_for(
                                    delta_future,
                                    timeout=3 / 4 * OPS_TIMEOUT,
                                    loop=event_loop,
                                )
                            except concurrent.futures.process.BrokenProcessPool:
                                # the process was somehow killed
                                logger.error(
                                    f'sink [{sock.addr}] diff process was killed externally - sending pickle ([{len(new_pickle)}] bytes) instead'
                                )
                                data_type = SINK_DATA_TYPE_PICKLE
                            except asyncio.TimeoutError:
                                # the process timed out
                                try:
                                    delta_exc = delta_future.exception(timeout=0)
                                    logger.error(f'delta error: {delta_exc}')
                                except concurrent.futures.TimeoutError:
                                    logger.error('AHH')
                                logger.error(
                                    f'sink [{sock.addr}] diff process timed out - sending pickle ([{len(new_pickle)}] bytes) instead'
                                )
                                data_type = SINK_DATA_TYPE_PICKLE
                            else:
                                if len(delta) < len(new_pickle):
                                    # will send delta to remote client
                                    logger.debug(
                                        f'sink [{sock.addr}] will send delta of [{len(delta)}] bytes'
                                    )
                                    data_type = SINK_DATA_TYPE_DELTA
                                    data_to_send = delta
                                else:
                                    # the delta is actually longer than the pickle data, so just send the pickle
                                    logger.debug(
                                        f'sink [{sock.addr}] delta ([{len(delta)}] bytes) is longer than the pickle ([{len(new_pickle)}] bytes) - sending pickle'
                                    )
                                    data_type = SINK_DATA_TYPE_PICKLE
                    else:
                        data_type = SINK_DATA_TYPE_PICKLE
                    last_pickle = new_pickle
                else:
                    # keepalive message metadata
                    data_type = SINK_DATA_TYPE_PICKLE

                try:
                    await asyncio.wait_for(
                        sock.send_msg(data_to_send, meta_data=data_type),
                        timeout=OPS_TIMEOUT / 4,
                    )
                    logger.debug(f'sink [{sock.addr}] sent [{len(data_to_send)}] bytes')
                except (ConnectionError, asyncio.TimeoutError):
                    logger.info(
                        f'sink [{sock.addr}] disconnected or isn\'t accepting data - dropping connection'
                    )
                    raise asyncio.CancelledError
        except asyncio.CancelledError:
            raise
        finally:
            self.sinks.pop(sink_id)
            logger.debug(f'dropped sink [{sock.addr}]')


class DataServer:
    """The server has a set of DataSet objects. Each has 1 data source, and any number of data sinks. Pickled object data from the source is received on its socket, then transferred to the FIFO of every sink. The pickle is then sent out on the sink's socket.
    If the sink is remote, then sending a full pickle of the data every time will probably be network-bandwidth limited. Instead, if the sink has previous data available, it runs a diff algorithm (xdelta3) with the new and previous data to generate a 'delta', which is sent out instead of the pickle. The remote client can then reconstruct the data using the delta.

    i.e.
    self.datasets = {

    'dataset1' : DataSet(
                        ------> FIFO ------> diff ------> socket (remote client)
                       /
    socket (source) ----------> FIFO ------> diff ------> socket (remote client)
                       \
                        ------> FIFO -------------------> socket (local client)
    ),

    'dataset2' : DataSet(
                        ------> FIFO ------> diff ------> socket (remote client)
                       /
    socket (source) ----------> FIFO -------------------> socket (local client)
                       \
                        ------> FIFO -------------------> socket (local client)
    ),

    ... }

    """

    def __init__(self, port: int = DATASERV_PORT):
        """port: TCP/IP port of the data server"""
        self.port = port
        # a dictionary with string identifiers mapping to DataSet objects
        self.datasets: Dict[str, DataSet] = {}
        # asyncio event loop for running all the server tasks
        self.event_loop = asyncio.new_event_loop()

    def serve_forever(self):
        """Run the asyncio event loop - ayncio requires this be run in the main thread if
        processes are to be spawned from the event loop
        https://docs.python.org/3/library/asyncio-dev.html"""
        self.event_loop.set_debug(True)
        try:
            self.event_loop.run_until_complete(self._main())
        except RuntimeError:
            # event loop was stopped
            pass
        finally:
            cleanup_event_loop(self.event_loop)
            logger.info('data server closed')

    def stop(self):
        """Stop the event loop"""
        if self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        else:
            raise DataServerError(
                'tried stopping the data server but it isn\'t running!'
            )

    async def _main(self):
        """Socket server listening coroutine"""

        # call self.negotiation when a new client connects
        # force ipv4
        server = await asyncio.start_server(
            self._negotiation, 'localhost', self.port, family=socket.AF_INET
        )

        addr = server.sockets[0].getsockname()
        logger.info(f'Serving on {addr}')

        async with server:
            await server.serve_forever()

    async def _negotiation(self, sock_reader, sock_writer):
        """Coroutine that determines what kind of client has connected, and deal
        with it accordingly"""

        # custom socket wrapper for sending / receiving structured messages
        sock = CustomSock(sock_reader, sock_writer)

        logger.info(f'new client connection from [{sock.addr}]')

        try:
            try:
                # the first message we receive from the client should identify
                # what kind of client it is
                client_type, client_type_metadata = await asyncio.wait_for(
                    sock.recv_msg(), timeout=NEGOTIATION_TIMEOUT
                )
            except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                logger.warning(
                    f'connection with client [{sock.addr}] failed before it '
                    'identified itself during the negotiation phase'
                )
                try:
                    await sock.close()
                except IOError:
                    pass
                return

            # info client
            if client_type == NEGOTIATION_INFO:
                logger.info(f'client [{sock.addr}] is type [info]')
                # the client is requesting general info about the server
                # tell the client which datasets are available
                data = ','.join(list(self.datasets.keys())).encode()
                try:
                    await asyncio.wait_for(
                        sock.send_msg(data), timeout=NEGOTIATION_TIMEOUT
                    )
                except (ConnectionError, asyncio.TimeoutError):
                    logger.warning(
                        f'server failed sending data to [info] client [{sock.addr}]'
                    )
                try:
                    await sock.close()
                except IOError:
                    pass
                return

            # data source client
            elif client_type == NEGOTIATION_SOURCE:
                logger.info(f'client [{sock.addr}] is type [source]')
                # the client will be a data source for a dataset on the server
                # first we need know which dataset it will provide data for
                try:
                    dataset_name_bytes, _ = await asyncio.wait_for(
                        sock.recv_msg(), timeout=NEGOTIATION_TIMEOUT
                    )
                except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                    logger.warning(
                        f'failed getting the data set name from client [{sock.addr}]'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    return

                dataset_name = dataset_name_bytes.decode()

                if dataset_name not in self.datasets:
                    # create a new DataSet
                    self.datasets[dataset_name] = DataSet()

                # the server already contains a dataset with this name
                if self.datasets[dataset_name].source:
                    # the dataset already has a source
                    logger.warning(
                        f'client [{sock.addr}] wants to source data '
                        f'for data set [{dataset_name}], but it already has a source - dropping connection'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    return
                else:
                    logger.info(
                        f'client [{sock.addr}] sourcing data for data set [{dataset_name}]'
                    )
                    # the dataset exists and it's original source is gone, so the client
                    # will act as the new source
                    await self.datasets[dataset_name].run_source(sock)

            # data sink client
            elif client_type == NEGOTIATION_SINK:
                logger.info(f'client [{sock.addr}] is type [sink]')
                # get the dataset name
                try:
                    dataset_name_bytes, _ = await asyncio.wait_for(
                        sock.recv_msg(), timeout=NEGOTIATION_TIMEOUT
                    )
                except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                    logger.warning(
                        f'failed getting the data set name from client [{sock.addr}]'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    return

                dataset_name = dataset_name_bytes.decode()

                if dataset_name in self.datasets:
                    logger.info(
                        f'client [{sock.addr}] sinking data from data set [{dataset_name}]'
                    )
                    if client_type_metadata in (
                        SINK_DATA_TYPE_PICKLE,
                        SINK_DATA_TYPE_DELTA,
                        SINK_DATA_TYPE_DEFAULT,
                    ):
                        # add the client to the sinks for the requested dataset
                        await self.datasets[dataset_name].run_sink(
                            self.event_loop, sock, client_type_metadata
                        )
                    else:
                        logger.error(
                            f'sink client received unknown data type [{client_type_metadata}] from the data server [{sock.addr}]'
                        )
                        try:
                            await sock.close()
                        except IOError:
                            pass
                        return
                else:
                    # the requested dataset isn't available on the server
                    logger.warning(
                        f'client [{sock.addr}] wants to sink data from data set [{dataset_name}], but it doesn\'t exist - dropping connection'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    return
            # unknown client type
            else:
                # the client gave an invalid connection type
                logger.error(
                    f'client [{sock.addr}] provided an invalid connection type [{client_type}] - dropping connection'
                )
                try:
                    await sock.close()
                except IOError:
                    pass
                return
        except asyncio.CancelledError:
            logger.debug(
                f'communication with client [{sock.addr}] cancelled - closing connection'
            )
            try:
                await sock.close()
            except IOError:
                pass
            raise

    def __enter__(self):
        """Python context manager setup"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.stop()


class DataSource:
    """For sourcing data to a DataServer"""

    def __init__(self, name: str, addr: str = 'localhost', port: int = DATASERV_PORT):
        # name of the dataset
        self.name = name
        # dict mapping the object name to the watched object itself
        self.data: Dict[str, Any] = {}
        # IP address of the data server to connect to
        self.addr = addr
        # port of the data server to connect to
        self.port = port
        # asyncio event loop for sending/receiving data to/from the socket
        self.event_loop = asyncio.new_event_loop()
        # thread for running self.event_loop
        self.thread = Thread(target=self._event_loop_thread)
        self.thread.start()

    def add(self, name, obj):
        """Add a new object to the data set"""
        if name not in self.data:
            self.data[name] = obj
        else:
            raise DataServerError(
                f'An object with the name "{name}" already exists in the data set'
            )

    def _event_loop_thread(self):
        """Run the asyncio event loop - this may be run in a separate thread because
        we aren't starting any subprocesses or responding to signals"""
        self.event_loop.set_debug(True)
        try:
            self.event_loop.run_until_complete(self._main())
        except RuntimeError:
            # event loop was stopped
            logger.debug(f'source [{(self.addr, self.port)}] stopping...')
        finally:
            cleanup_event_loop(self.event_loop)
            logger.info(f'source [{(self.addr, self.port)}] closed')

    def stop(self):
        """Stop the event loop"""
        if self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        else:
            raise DataServerError('tried stopping the source but it isn\'t running!')

    async def _main(self):
        """asyncio main loop"""
        # asyncio queue for buffering pickles to send to the server
        self.queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        try:
            while True:
                try:
                    # connect to the data server
                    sock_reader, sock_writer = await asyncio.wait_for(
                        asyncio.open_connection(self.addr, self.port),
                        timeout=NEGOTIATION_TIMEOUT,
                    )
                except OSError:
                    logger.warning(
                        f'source failed connecting to data server [{(self.addr, self.port)}]'
                    )
                    await asyncio.sleep(FAST_TIMEOUT)
                    continue

                sock = CustomSock(sock_reader, sock_writer)
                logger.info(f'source connected to data server [{sock.addr}]')

                try:
                    # notify the server that this is a data source client
                    await asyncio.wait_for(
                        sock.send_msg(NEGOTIATION_SOURCE),
                        timeout=NEGOTIATION_TIMEOUT,
                    )
                    # send the dataset name
                    await asyncio.wait_for(
                        sock.send_msg(self.name.encode()),
                        timeout=NEGOTIATION_TIMEOUT,
                    )
                except (ConnectionError, asyncio.TimeoutError):
                    logger.warning(
                        f'source failed negotiation process with data server [{sock.addr}] - attempting reconnect'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    await asyncio.sleep(FAST_TIMEOUT)
                    continue

                logger.debug(
                    f'source finished negotiation with data server [{sock.addr}]'
                )

                while True:
                    try:
                        # get pickle data from the queue
                        new_data = await asyncio.wait_for(
                            self.queue.get(), timeout=KEEPALIVE_TIMEOUT
                        )
                        self.queue.task_done()
                        logger.debug(
                            f'source dequeued pickle of [{len(new_data)}] bytes - sending to data server [{sock.addr}]'
                        )
                    except asyncio.TimeoutError:
                        # if there's no data available, send a keepalive message
                        new_data = b''
                        logger.debug('source sending keepalive to data server')
                    # send the data to the server
                    try:
                        await asyncio.wait_for(
                            sock.send_msg(new_data), timeout=OPS_TIMEOUT
                        )
                        logger.debug(
                            f'source sent pickle of [{len(new_data)}] bytes to data server [{sock.addr}]'
                        )
                    except (ConnectionError, asyncio.TimeoutError):
                        logger.warning(
                            f'source failed sending to data server [{sock.addr}] - attempting reconnect'
                        )
                        try:
                            await sock.close()
                        except IOError:
                            pass
                        break
        except asyncio.CancelledError:
            logger.debug(
                f'source stopped, closing connection with data server [{sock.addr}]'
            )
            try:
                await sock.close()
            except IOError:
                pass
            raise

    async def _push(self, new_pickle):
        """Coroutine that puts a pickle onto the queue"""
        try:
            try:
                self.queue.put_nowait(new_pickle)
            except asyncio.QueueFull:
                # the server isn't accepting data fast enough
                # so we will empty the queue and place only this most recent
                # piece of data on it
                logger.debug(
                    f'data server [{(self.addr, self.port)}] can\'t keep up with source'
                )
                # empty the queue then put a single item into it
                queue_flush_and_put(self.queue, new_pickle)
            logger.debug(f'source queued pickle of [{len(new_pickle)}] bytes')
        except asyncio.CancelledError:
            logger.debug('source push cancelled')
            raise

    def _serialize(self, obj) -> bytes:
        """Serialize a python object into a byte stream"""
        return pickle.dumps(obj)

    def update(self):
        """User-facing function for pushing new data to the server"""
        # serialize the objects
        new_pickle = self._serialize(self.data)
        logger.debug(f'source pushing object of [{len(new_pickle)}] bytes pickled')
        # put it on the queue
        future = asyncio.run_coroutine_threadsafe(
            self._push(new_pickle), self.event_loop
        )
        # wait for the coroutine to return
        future.result()

    def __enter__(self):
        """Python context manager setup"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.stop()


class DataSink:
    """For sinking data from a DataServer"""

    def __init__(
        self,
        name: str,
        addr: str = 'localhost',
        port: int = DATASERV_PORT,
        data_type_override: bytes = SINK_DATA_TYPE_DEFAULT,
    ):
        # name of the dataset
        self.name = name
        # dict mapping the object name to the watched object
        self.data: Dict[str, Any] = {}
        # IP address of the data server to connect to
        self.addr = addr
        # port of the data server to connect to
        self.port = port
        # asyncio event loop for sending/receiving data to/from the socket
        self.event_loop = asyncio.new_event_loop()
        # request that, whenever possible, the server send data as a specific type - set to:
        # SINK_DATA_TYPE_DEFAULT for the server to decide whether diffs should be performed
        # SINK_DATA_TYPE_PICKLE to always use pickle data (no diff)
        # SINK_DATA_TYPE_DELTA to always generate a diff
        self.data_type_override = data_type_override
        # thread for running self.event_loop
        self.thread = Thread(target=self._event_loop_thread)
        self.thread.start()

    def _event_loop_thread(self):
        """Run the asyncio event loop - this may be run in a separate thread because
        we aren't starting any subprocesses or responding to signals"""
        self.event_loop.set_debug(True)
        try:
            self.event_loop.run_until_complete(self._main())
        except RuntimeError:
            # event loop was stopped
            logger.debug(f'sink [{(self.addr, self.port)}] stopping...')
        finally:
            cleanup_event_loop(self.event_loop)
            logger.info(f'sink [{(self.addr, self.port)}] closed')

    def stop(self):
        """Stop the event loop"""
        if self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        else:
            raise DataServerError('tried stopping the data sink but it isn\'t running!')

    async def _main(self):
        """asyncio main loop"""
        # asyncio queue for buffering data from the server
        self.queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        try:
            while True:
                try:
                    # connect to the data server
                    sock_reader, sock_writer = await asyncio.wait_for(
                        asyncio.open_connection(self.addr, self.port),
                        timeout=NEGOTIATION_TIMEOUT,
                    )
                except OSError:
                    logger.warning(
                        f'sink failed connecting to data server [{(self.addr, self.port)}]'
                    )
                    await asyncio.sleep(FAST_TIMEOUT)
                    continue

                sock = CustomSock(sock_reader, sock_writer)
                logger.info(f'sink connected to data server [{sock.addr}]')

                try:
                    # notify the server that this is a data sink client
                    await asyncio.wait_for(
                        sock.send_msg(
                            NEGOTIATION_SINK, meta_data=self.data_type_override
                        ),
                        timeout=NEGOTIATION_TIMEOUT,
                    )
                    # send the dataset name
                    await asyncio.wait_for(
                        sock.send_msg(self.name.encode()),
                        timeout=NEGOTIATION_TIMEOUT,
                    )
                except (ConnectionError, asyncio.TimeoutError):
                    logger.warning(
                        f'sink failed negotiation process with data server [{sock.addr}] - attempting reconnect'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    await asyncio.sleep(FAST_TIMEOUT)
                    continue

                logger.debug(
                    f'sink finished negotiation with data server [{sock.addr}]'
                )

                last_pickle = None
                while True:
                    try:
                        # get data from the server
                        new_data, data_type = await asyncio.wait_for(
                            sock.recv_msg(), timeout=TIMEOUT
                        )
                    except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                        # if there was a timeout / problem receiving the message the dataserver / connection is dead
                        logger.warning(
                            f'sink data server [{sock.addr}] disconnected or hasn\'t sent a keepalive message - dropping connection'
                        )
                        try:
                            await sock.close()
                        except IOError:
                            pass
                        break

                    if not new_data:
                        # keepalive message
                        continue

                    if data_type == SINK_DATA_TYPE_PICKLE:
                        logger.debug(
                            f'sink received pickle of [{len(new_data)}] bytes from data server [{sock.addr}]'
                        )
                        new_pickle = new_data
                    elif data_type == SINK_DATA_TYPE_DELTA:
                        # if the server sent a delta, we will first reconstruct the pickle
                        logger.debug(
                            f'sink received delta of [{len(new_data)}] bytes from data server [{sock.addr}]'
                        )
                        if last_pickle:
                            new_pickle = xdelta3.decode(last_pickle, new_data)
                        else:
                            logger.error(
                                f'sink received delta data from the data server [{sock.addr}] but hasn\'t received a pickle yet'
                            )
                            try:
                                await sock.close()
                            except IOError:
                                pass
                            break
                    else:
                        logger.error(
                            f'sink received unknown data type [{data_type}] from the data server [{sock.addr}]'
                        )
                        try:
                            await sock.close()
                        except IOError:
                            pass
                        break

                    last_pickle = new_pickle

                    try:
                        # put pickle on the queue
                        self.queue.put_nowait(new_pickle)
                    except asyncio.QueueFull:
                        # the user isn't consuming data fast enough so we will empty the queue and place only this most recent pickle on it
                        logger.debug(
                            'pop() isn\'t being called frequently enough to keep up with data source'
                        )
                        # empty the queue then put a single item into it
                        queue_flush_and_put(self.queue, new_pickle)
                    logger.debug(f'sink queued pickle of [{len(new_pickle)}] bytes')
                await asyncio.sleep(FAST_TIMEOUT)

        except asyncio.CancelledError:
            logger.debug(
                f'sink stopped, closing connection with data server [{sock.addr}]'
            )
            try:
                await sock.close()
            except IOError:
                pass
            raise

    async def _pop(self, timeout) -> bytes:
        """Coroutine that gets data from the queue"""
        try:
            # get pickle data from the queue
            new_pickle = await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except asyncio.CancelledError:
            logger.debug('pop cancelled')
            raise
        else:
            self.queue.task_done()
            return new_pickle

    def _deserialize(self, obj) -> bytes:
        """Deserialize a python object from a byte stream"""
        return pickle.loads(obj)

    def update(self, timeout=None):
        """User-facing function for popping new data from the server"""
        # get the most recent pickle from the queue
        future = asyncio.run_coroutine_threadsafe(self._pop(timeout), self.event_loop)
        try:
            # wait for the coroutine to return
            new_pickle = future.result()
        except asyncio.TimeoutError:
            # raise TimeoutError if no pickle is available
            raise TimeoutError
        logger.debug(f'pop returning [{len(new_pickle)}] bytes unpickled')
        # update objects
        self.data = self._deserialize(new_pickle)

    def __getattr__(self, attr: str):
        """Allow the user to access the data objects using sink.obj notation"""
        if attr in self.data:
            return self.data[attr]
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)

    def __enter__(self):
        """Python context manager setup"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.stop()
