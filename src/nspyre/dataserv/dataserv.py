"""
The nspyre DataServer transports arbitrary python objects over a TCP/IP socket
to a set of local or remote network clients, and keeps those objects up to date
as they are modified. For each data set on the data server, there is a single
data "source", and a set of data "sinks".

Objects are serialized by the source then pushed to the server. For local
clients, the data server sends the serialized data directly to the be
deserialized by the sink process. For remote clients, the serialized object
data is diffed with any previously pushed data and the diff is sent rather than
the full object in order to minimize the required network bandwidth. The client
can then reconstruct the pushed data using a local copy of the last version of
the object, and the diff received from the server.

Example usage:

# run the command-line tool for starting up the data server, specifying the port
nspyre-dataserv -p 12345

# see DataSink.pop()

Author: Jacob Feder
Date: 11/29/2020
"""
import asyncio
import concurrent.futures
import logging
import pickle
import selectors
import socket
from threading import Semaphore
from threading import Thread
from typing import Any
from typing import Dict

# lazy import xdelta3
try:
    import xdelta3
except ModuleNotFoundError:
    xdelta3 = None

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
# TODO runtime control of the data server (maybe with rpyc?)
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


async def cleanup_event_loop(loop):
    """End all tasks in an event loop and exit"""

    if not loop.is_running():
        logger.warning('Ignoring loop cleanup request because the loop isn\'t running.')
        return

    # gather all of the tasks except this one
    pending_tasks = []
    for task in asyncio.all_tasks(loop=loop):
        if task is not asyncio.current_task():
            pending_tasks.append(task)

    # cancel each pending task
    for task in pending_tasks:
        task.cancel()
    # wait for all tasks to exit
    await asyncio.gather(*pending_tasks, return_exceptions=True)

    # shut down the event loop
    loop.stop()


def deserialize(obj) -> Any:
    """Deserialize a python object from a byte stream."""
    return pickle.loads(obj)


def serialize(obj) -> bytes:
    """Serialize a python object into a byte stream."""
    return pickle.dumps(obj)


class DataSet:
    """Class that wraps a pipeline consisting of a data source and a list of data sinks."""

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
        # object to store the most up-to-date data for safekeeping
        self.data = None

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
        # create a queue for the sink
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        # add the sink data to the DataSet
        sink_dict = {
            'task': task,
            'sock': sock,
            'queue': queue,
        }
        self.sinks[sink_id] = sink_dict
        if self.data:
            # push the current data to the sink so it has a starting point
            queue.put_nowait(self.data)
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
                except (asyncio.IncompleteReadError, asyncio.TimeoutError) as exc:
                    # if there was a timeout / problem receiving the message
                    # the source client is dead and will be terminated
                    logger.debug(
                        f'source [{sock.addr}] disconnected or hasn\'t sent a keepalive message - dropping connection'
                    )
                    raise asyncio.CancelledError from exc

                if len(new_pickle):
                    self.data = new_pickle
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
        except asyncio.CancelledError as exc:
            raise asyncio.CancelledError from exc
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
                            and xdelta3
                        )
                    ):
                        if not xdelta3:
                            raise ModuleNotFoundError(
                                'The data server was requested to use the xdelta3 protocol but the xdelta3 module isn\'t installed.'
                            )
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
                except (ConnectionError, asyncio.TimeoutError) as exc:
                    logger.info(
                        f'sink [{sock.addr}] disconnected or isn\'t accepting data - dropping connection'
                    )
                    raise asyncio.CancelledError from exc
        except asyncio.CancelledError as exc:
            raise asyncio.CancelledError from exc
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
        # TODO for some reason there are performance issues on windows when using the ProactorEventLoop
        selector = selectors.SelectSelector()
        self.event_loop = asyncio.SelectorEventLoop(selector)

    def serve_forever(self):
        """Run the asyncio event loop - ayncio requires this be run in the main thread if
        processes are to be spawned from the event loop. See https://docs.python.org/3/library/asyncio-dev.html."""
        self.event_loop.set_debug(True)
        asyncio.set_event_loop(self.event_loop)
        try:
            self.event_loop.call_soon(self._main_helper)
            self.event_loop.run_forever()
        finally:
            self.event_loop.close()
            logger.info('data server closed')

    def stop(self):
        """Stop the asyncio event loop."""
        if self.event_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                cleanup_event_loop(self.event_loop), self.event_loop
            )
        else:
            raise RuntimeError('tried stopping the data server but it isn\'t running!')

    def _main_helper(self):
        """Callback function to start _main"""
        asyncio.create_task(self._main())

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
        except ConnectionResetError:
            logger.debug(f'client [{sock.addr}] forcibly closed - closing connection')
        except asyncio.CancelledError as exc:
            logger.debug(
                f'communication with client [{sock.addr}] cancelled - closing connection'
            )
            try:
                await sock.close()
            except IOError:
                pass
            raise asyncio.CancelledError from exc

    def __enter__(self):
        """Python context manager setup"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.stop()


class DataSource:
    """For sourcing data to a DataServer"""

    def __init__(self, name: str, addr: str = 'localhost', port: int = DATASERV_PORT, auto_reconnect: bool = False):
        """Initialize connection to the data set on the server.

        See DataSink.pop() for typical usage example.

        Args:
            name: Name of the data set.
            addr: Network address of the data server.
            port: Port of the data server.
            auto_reconnect: If True, automatically reconnect to the data server if it is disconnected. Otherwise raise an error if connection fails.
        """

        # name of the dataset
        self._name = name

        # IP address of the data server to connect to
        self._addr = addr

        # port of the data server to connect to
        self._port = port

        # asyncio event loop for sending/receiving data to/from the socket
        selector = selectors.SelectSelector()
        self._event_loop = asyncio.SelectorEventLoop(selector)

        # store exceptions thrown in the event loop (running in another thread)
        self._exc = None

        # whether the source should try to reconnect to the data server
        self._auto_reconnect = auto_reconnect

    def _check_exc(self):
        """Check to see if an exception was raised in the event loop thread."""
        if self._exc is not None:
            raise self._exc

    def start(self):
        """Start the asyncio event loop that connects to the data server and serves pop requests."""
        # thread for running self._event_loop
        self._thread = Thread(target=self._event_loop_thread, daemon=True)
        self._thread.start()
        # semaphore to block until connection has occurred
        self._sem = Semaphore(value=0)
        self._sem.acquire()
        self._check_exc()

    def _event_loop_thread(self):
        """Run the asyncio event loop - this may be run in a separate thread because
        we aren't starting any subprocesses or responding to signals"""
        logging.debug(f'started DataSource event loop thread {self._thread}')
        self._event_loop.set_debug(True)
        asyncio.set_event_loop(self._event_loop)
        try:
            self._event_loop.call_soon(self._main_helper)
            self._event_loop.run_forever()
        finally:
            self._event_loop.close()
            logger.info(f'source [{(self._addr, self._port)}] closed')

    def stop(self, timeout=3):
        """Stop the asyncio event loop.
        
        Args:
            timeout: time to wait to shut down the event loop.
        """
        if self._event_loop.is_running():
            # wait for the queue to be empty (with timeout) to allow any pushes in the pipeline to be sent
            future = asyncio.run_coroutine_threadsafe(
                self._queue.join(), self._event_loop
            )
            # wait for the coroutine to return
            try:
                future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                logger.info(
                    'Timed out waiting for the DataSource queue to be empty. Stopping anyway...'
                )
                future.cancel()
                return
            except concurrent.futures.CancelledError:
                logging.error('queue.join() was cancelled. This is shouldn\'t happen.')
            # kill the event loop
            asyncio.run_coroutine_threadsafe(
                cleanup_event_loop(self._event_loop), self._event_loop
            )
        else:
            raise RuntimeError('tried stopping the source but it isn\'t running!')

    def _main_helper(self):
        """Callback function to start _main"""
        asyncio.create_task(self._main())

    async def _main(self):
        """asyncio main loop"""
        try:
            # asyncio queue for buffering pickles to send to the server
            self._queue = asyncio.Queue(maxsize=QUEUE_SIZE)
            while True:
                try:
                    # connect to the data server
                    sock_reader, sock_writer = await asyncio.wait_for(
                        asyncio.open_connection(self._addr, self._port),
                        timeout=NEGOTIATION_TIMEOUT,
                    )
                except OSError as err:
                    logger.warning(
                        f'source failed connecting to data server [{(self._addr, self._port)}]'
                    )
                    await asyncio.sleep(FAST_TIMEOUT)
                    if self._auto_reconnect:
                        continue
                    else:
                        raise ConnectionError(
                            f'Failed connecting to data server [{(self._addr, self._port)}]'
                        ) from err

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
                        sock.send_msg(self._name.encode()),
                        timeout=NEGOTIATION_TIMEOUT,
                    )
                except (ConnectionError, asyncio.TimeoutError) as err:
                    logger.warning(
                        f'source failed negotiation process with data server [{sock.addr}] - attempting reconnect'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    await asyncio.sleep(FAST_TIMEOUT)
                    if self._auto_reconnect:
                        continue
                    else:
                        raise ConnectionError(
                            f'Failed connecting to data server [{(self._addr, self._port)}]'
                        ) from err

                logger.debug(
                    f'source finished negotiation with data server [{sock.addr}]'
                )

                # connection succeeded, so trigger the main thread to continue execution
                self._sem.release()

                while True:
                    try:
                        # get pickle data from the queue
                        new_data = await asyncio.wait_for(
                            self._queue.get(), timeout=KEEPALIVE_TIMEOUT
                        )
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
                        if new_data:
                            # mark that the queue data has been fully processed
                            self._queue.task_done()
                    except (ConnectionError, asyncio.TimeoutError):
                        logger.warning(
                            f'source failed sending to data server [{sock.addr}] - attempting reconnect'
                        )
                        try:
                            await sock.close()
                        except IOError:
                            pass
                        break
        except ConnectionError as err:
            self._exc = err
            # release the main thread if there's a connection error
            self._sem.release()
        except asyncio.CancelledError as exc:
            logger.debug(
                f'source stopped, closing connection with data server [{sock.addr}]'
            )
            try:
                await sock.close()
            except (IOError, NameError):
                # socket is broken or hasn't been created yet
                pass
            raise asyncio.CancelledError from exc

    async def _push(self, new_pickle):
        """Coroutine that puts a pickle onto the queue"""
        try:
            try:
                self._queue.put_nowait(new_pickle)
            except asyncio.QueueFull:
                # the server isn't accepting data fast enough
                # so we will empty the queue and place only this most recent
                # piece of data on it
                logger.debug(
                    f'data server [{(self._addr, self._port)}] can\'t keep up with source'
                )
                # empty the queue then put a single item into it
                queue_flush_and_put(self._queue, new_pickle)
            logger.debug(f'source queued pickle of [{len(new_pickle)}] bytes')
        except asyncio.CancelledError:
            logger.debug('source push cancelled')
            raise

    def push(self, data):
        """Push new data to the data server.

        Args:
            data: Any python object (must be pickleable) to send. Ideally, this should be a dictionary to allow for simple attribute access from the sink side like `sink.my_var`.
        """
        # serialize the objects
        new_pickle = serialize(data)
        logger.debug(f'source pushing object of [{len(new_pickle)}] bytes pickled')
        # put it on the queue
        future = asyncio.run_coroutine_threadsafe(
            self._push(new_pickle), self._event_loop
        )
        # wait for the coroutine to return
        try:
            future.result()
        except concurrent.futures.TimeoutError:
            logger.error(
                '_push timed out (this shouldn\'t happen since timeout is handled by _push itself)'
            )
            future.cancel()
        except concurrent.futures.CancelledError:
            logging.debug('_push was cancelled')
        self._check_exc()

    def __enter__(self):
        """Python context manager setup"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.stop()

    def __del__(self):
        if self._event_loop.is_running():
            logger.warning(
                f'DataSource {self} event loop is still running. Did you forget to call stop()?'
            )


class DataSink:
    """For sinking data from a DataServer"""

    def __init__(
        self,
        name: str,
        addr: str = 'localhost',
        port: int = DATASERV_PORT,
        auto_reconnect: bool = False,
        data_type_override: bytes = SINK_DATA_TYPE_DEFAULT,
    ):
        """Initialize connection to the data set on the server.

        Args:
            name: Name of the data set.
            addr: Network address of the data server.
            port: Port of the data server.
            auto_reconnect: If True, automatically reconnect to the data server if it is disconnected. Otherwise raise an error if connection fails.
            data_type_override: Specify SINK_DATA_TYPE_PICKLE to force the data server to only send pickled data over the network, SINK_DATA_TYPE_DELTA to send delta objects, or SINK_DATA_TYPE_DEFAULT to choose automatically.
        """

        # name of the dataset
        self._name = name

        # dict mapping the object name to the watched object
        self.data: Dict[str, Any] = {}

        # IP address of the data server to connect to
        self._addr = addr

        # port of the data server to connect to
        self._port = port

        # asyncio event loop for sending/receiving data to/from the socket
        selector = selectors.SelectSelector()
        self._event_loop = asyncio.SelectorEventLoop(selector)

        # store exceptions thrown in the event loop (running in another thread)
        self._exc = None

        # whether the sink should try to reconnect to the data server
        self._auto_reconnect = auto_reconnect

        # request that, whenever possible, the server send data as a specific type - set to:
        # SINK_DATA_TYPE_DEFAULT for the server to decide whether diffs should be performed
        # SINK_DATA_TYPE_PICKLE to always use pickle data (no diff)
        # SINK_DATA_TYPE_DELTA to always generate a diff
        self._data_type_override = data_type_override

    def _check_exc(self):
        """Check to see if an exception was raised in the event loop thread."""
        if self._exc is not None:
            raise self._exc

    def start(self):
        """Start the asyncio event loop that connects to the data server and serves pop requests."""
        # thread for running self._event_loop
        self._thread = Thread(target=self._event_loop_thread, daemon=True)
        self._thread.start()
        # semaphore to block until connection has occurred
        self._sem = Semaphore(value=0)
        self._sem.acquire()
        self._check_exc()

    def stop(self):
        """Stop the asyncio event loop."""
        if self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                cleanup_event_loop(self._event_loop), self._event_loop
            )
        else:
            raise RuntimeError('tried stopping the data sink but it isn\'t running!')

    def _event_loop_thread(self):
        """Run the asyncio event loop - this may be run in a separate thread because
        we aren't starting any subprocesses or responding to signals"""
        logging.debug(f'started DataSource event loop thread {self._thread}')
        self._event_loop.set_debug(True)
        asyncio.set_event_loop(self._event_loop)
        try:
            self._event_loop.call_soon(self._main_helper)
            self._event_loop.run_forever()
        finally:
            self._event_loop.close()
            logger.info(f'sink [{(self._addr, self._port)}] closed')

    def _main_helper(self):
        """Callback function to start _main"""
        # TODO for some reason this takes a long time
        asyncio.create_task(self._main())

    async def _main(self):
        """asyncio main loop"""
        try:
            # asyncio queue for buffering data from the server
            self._queue = asyncio.Queue(maxsize=QUEUE_SIZE)

            while True:
                try:
                    # connect to the data server
                    sock_reader, sock_writer = await asyncio.wait_for(
                        asyncio.open_connection(self._addr, self._port),
                        timeout=NEGOTIATION_TIMEOUT,
                    )
                except OSError as err:
                    logger.warning(
                        f'sink failed connecting to data server [{(self._addr, self._port)}]'
                    )
                    await asyncio.sleep(FAST_TIMEOUT)
                    if self._auto_reconnect:
                        continue
                    else:
                        raise ConnectionError(
                            f'Failed connecting to data server [{(self._addr, self._port)}]'
                        ) from err

                sock = CustomSock(sock_reader, sock_writer)
                logger.info(f'sink connected to data server [{sock.addr}]')

                try:
                    # notify the server that this is a data sink client
                    await asyncio.wait_for(
                        sock.send_msg(
                            NEGOTIATION_SINK, meta_data=self._data_type_override
                        ),
                        timeout=NEGOTIATION_TIMEOUT,
                    )
                    # send the dataset name
                    await asyncio.wait_for(
                        sock.send_msg(self._name.encode()),
                        timeout=NEGOTIATION_TIMEOUT,
                    )
                except (ConnectionError, asyncio.TimeoutError) as err:
                    logger.warning(
                        f'sink failed negotiation process with data server [{sock.addr}] - attempting reconnect'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    await asyncio.sleep(FAST_TIMEOUT)
                    if self._auto_reconnect:
                        continue
                    else:
                        raise ConnectionError(
                            f'Failed connecting to data server [{(self._addr, self._port)}]'
                        ) from err

                logger.debug(
                    f'sink finished negotiation with data server [{sock.addr}]'
                )

                # connection succeeded, so trigger the main thread to continue execution
                self._sem.release()

                last_pickle = None
                while True:
                    try:
                        # get data from the server
                        new_data, data_type = await asyncio.wait_for(
                            sock.recv_msg(), timeout=TIMEOUT
                        )
                    except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                        # if there was a timeout / problem receiving the message the dataserver / connection is dead
                        logger.info(
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
                        if not xdelta3:
                            raise ModuleNotFoundError(
                                'The data server sent a packet using the xdelta3 protocol but the xdelta3 module isn\'t installed.'
                            )
                        # if the server sent a delta, we will first reconstruct the pickle
                        logger.debug(
                            f'sink received delta of [{len(new_data)}] bytes from data server [{sock.addr}]'
                        )
                        if last_pickle:
                            new_pickle = xdelta3.decode(last_pickle, new_data)
                        else:
                            logger.error(
                                f'sink received delta data from the data server [{sock.addr}] but hasn\'t previously received a pickle'
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
                        self._queue.put_nowait(new_pickle)
                    except asyncio.QueueFull:
                        # the user isn't consuming data fast enough so we will empty the queue and place only this most recent pickle on it
                        logger.debug(
                            'pop() isn\'t being called frequently enough to keep up with data source'
                        )
                        # empty the queue then put a single item into it
                        queue_flush_and_put(self._queue, new_pickle)
                    logger.debug(f'sink queued pickle of [{len(new_pickle)}] bytes')
                await asyncio.sleep(FAST_TIMEOUT)

        except ConnectionError as err:
            self._exc = err
            # release the main thread if there's a connection error
            self._sem.release()
        except asyncio.CancelledError as err:
            logger.debug(
                f'sink stopped, closing connection with data server [{sock.addr}]'
            )
            try:
                await sock.close()
            except (IOError, NameError):
                # socket is broken or hasn't been created yet
                pass
            raise err

    async def _pop(self, timeout) -> bytes:
        """Coroutine that gets data from the queue"""
        try:
            # get pickle data from the queue
            new_pickle = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.CancelledError as exc:
            logger.debug('pop cancelled')
            raise asyncio.CancelledError from exc
        else:
            self._queue.task_done()
            return new_pickle

    def pop(self, timeout=None) -> bool:
        """Block waiting for an updated version of the data from the data server. Once the data is received, the internal data instance variable will be updated and the function will return.

        Typical usage example:

            First start the data server from the console on machine A:

            .. code-block:: console

                $ nspyre-dataserv

            Run the python program on machine A implementing the experimental logic:

            .. code-block:: python

                # machine A: "source"-side code
                # running on the same machine as the data server, in the same or a different process

                from nspyre import DataSource
                import numpy as np

                # connect to the data server and create a data set, or connect to an
                # existing one with the same name if it was created earlier
                with DataSource('my_dataset') as source:
                    # do an experiment where we measure voltage of something as a function of frequency
                    n = 100
                    frequencies = np.linspace(1e6, 100e6, n)
                    voltages = np.zeros(n)

                    for f in frequencies:
                        signal_generator.set_frequency(f)
                        voltages[i] = daq.get_voltage()
                        # push most up-to-date data to the server
                        source.push({'freq': frequencies, 'volts': voltages})

            Then run the python program on machine B implementing the data plotting:

            .. code-block:: python

                # machine B: "sink"-side code
                # running on a different machine as the source / data server

                from nspyre import DataSink

                # connect to the data set on the data server
                # IP of data server computer = '192.168.1.50'
                with DataSink('my_dataset', '192.168.1.50') as sink:
                    while True:
                        # block until an updated version of the data set is available
                        if sink.pop():
                            # sink.freq and sink.volts have been modified
                            # replot the data to show the new values
                            my_plot_update(sink.freq, sink.volts)

        Args:
            timeout: Time to wait for an update in seconds. Set to None to wait forever.

        Raises:
            TimeoutError: A timeout occured.

        Returns:
            bool: True if successful, False otherwise.

        """
        ret = False
        # get the most recent pickle from the queue
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._pop(timeout), self._event_loop
            )
        except RuntimeError:
            logger.debug('pop called but the sink is closed')

        try:
            # wait for the coroutine to return
            new_pickle = future.result()
        except concurrent.futures.TimeoutError:
            logger.error(
                '_pop timed out (this shouldn\'t happen since timeout is handled by _pop itself), cancelling the task...'
            )
            future.cancel()
        except concurrent.futures.CancelledError:
            logging.debug('_pop was cancelled')
        except asyncio.exceptions.TimeoutError as exc:
            raise TimeoutError('Pop timed out') from exc
        else:
            logger.debug(f'pop returning [{len(new_pickle)}] bytes unpickled')
            # update data object
            self.data = deserialize(new_pickle)
            ret = True
        self._check_exc()
        return ret

    def __getattr__(self, attr: str):
        """Allow the user to access the data objects using sink.obj notation"""
        if attr in self.data:
            return self.data[attr]
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)

    def __enter__(self):
        """Python context manager setup"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.stop()

    def __del__(self):
        if self._event_loop.is_running():
            logger.warning(
                f'DataSink {self} event loop is still running. Did you forget to call stop()?'
            )
