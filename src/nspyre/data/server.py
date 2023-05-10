"""
The nspyre data server transports arbitrary python objects over a TCP/IP socket
to a set of local or remote network clients, and keeps those objects up to date
as they are modified. For each data set on the data server, there is a single
data :py:class:`~nspyre.data.source.DataSource`, and a set of data
:py:class:`~nspyre.data.sink.DataSink`. The source pushes data to
the data server and each of the sinks pops data from the data server.

Objects are serialized by the source then pushed to the server. Each sink
receives a copy of the serialized objects, then deserializes them locally. If
the user makes use of "Streaming" objects such as the
:py:class:`~nspyre.data.streaming_list.StreamingList`, the source
will only serialize the operations that have been performed on the streaming
object since the last serialization. The sink can then reconstruct the pushed
data using a local copy of the last version of the object, and the diff
received from the data server. This is more efficient when data sets start
becoming larger and serialization performance is a bottleneck.

The data server can be started using the command-line interface, e.g.:

.. code-block:: console

   $ nspyre-dataserv -p 12345

"""
import asyncio
import logging
import selectors
import socket
from typing import Dict

from ._streaming_pickle import _squash_pickle_diff_queue
from ._streaming_pickle import deserialize_pickle_diff
from ._streaming_pickle import PickleDiff
from ._streaming_pickle import serialize_pickle_diff

_logger = logging.getLogger(__name__)

DATASERV_PORT = 30101
"""Default port to host the data server on."""

# if no data is available, any socket sender should send an empty message with an
# interval given by _KEEPALIVE_TIMEOUT (s)
_KEEPALIVE_TIMEOUT = 3
# time (s) that the sender has to do work before it should give up
# in order to prevent a timeout on its associated receiver
_OPS_TIMEOUT = 10
# timeout (s) for receive connections
_TIMEOUT = (_KEEPALIVE_TIMEOUT + _OPS_TIMEOUT) + 1

# maximum size of the data queue
_QUEUE_SIZE = 5

# indicates that the client is requesting some data about the server
_NEGOTIATION_INFO = b'\xDE'
# TODO runtime control of the data server (maybe with rpyc?)
# _NEGOTIATION_CMD = b'\xAD'
# indicates that the client will source data to the server
_NEGOTIATION_SOURCE = b'\xBE'
# indicates that the client will sink data from the server
_NEGOTIATION_SINK = b'\xEF'
# timeout (s) for send/recv operations during the client negotiation phase
_NEGOTIATION_TIMEOUT = _TIMEOUT

# timeout for relatively quick operations
_FAST_TIMEOUT = 1.0

# length (bytes) of the header section that identifies how large the payload is
_HEADER_MSG_LEN = 8


class _CustomSock:
    """Tiny socket wrapper class that implements a custom messaging protocol.
    recv_msg() and send_msg() use the following packet structure:
    |                      HEADER       | PAYLOAD
    | message length (excluding header) | message
    |        _HEADER_MSG_LEN            | variable length
    """

    def __init__(self, sock_reader, sock_writer):
        self.sock_reader = sock_reader
        self.sock_writer = sock_writer
        # (ip addr, port) of the client
        self.addr = sock_writer.get_extra_info('peername')

    async def recv_msg(self) -> bytes:
        """Receive a message through a socket by decoding the header then reading
        the rest of the message"""

        # the header bytes we receive from the client should identify
        # the length of the message payload
        msg_len_bytes = await self.sock_reader.readexactly(_HEADER_MSG_LEN)
        msg_len = int.from_bytes(msg_len_bytes, byteorder='little')

        # get the payload
        msg = await self.sock_reader.readexactly(msg_len)

        _logger.debug(f'Received [{msg_len}] bytes from [{self.addr}].')

        return msg

    async def send_msg(self, msg: bytes):
        """Send a byte message through a socket interface by encoding the header
        then sending the rest of the message"""

        # calculate the payload length and package it into bytes
        msg_len_bytes = len(msg).to_bytes(_HEADER_MSG_LEN, byteorder='little')

        # send the header + payload
        self.sock_writer.write(msg_len_bytes + msg)
        await self.sock_writer.drain()

        _logger.debug(f'Sent [{len(msg)}] bytes to {self.addr}.')

    async def close(self):
        """Fully close a socket connection"""
        self.sock_writer.close()
        await self.sock_writer.wait_closed()
        _logger.debug(f'Closed socket [{self.addr}].')


async def _cleanup_event_loop(loop):
    """End all tasks in an event loop and exit."""

    if not loop.is_running():
        _logger.warning(
            'Ignoring loop cleanup request because the loop isn\'t running.'
        )
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


class _DataSet:
    """Wraps a pipeline consisting of a data source and a list of data sinks."""

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
        # for storing the full history of the data
        self.pickle_diff = None

    async def run_sink(
        self,
        event_loop: asyncio.AbstractEventLoop,
        sock: _CustomSock,
    ):
        """Run a new data sink until it closes.

        Args:
            sock: socket for the sink
        """
        sink_id = sock.addr
        # sink connections should get unique ports, so this shouldn't happen
        assert sink_id not in self.sinks
        # create the sink task
        task = asyncio.create_task(self._sink_coro(event_loop, sink_id))
        # create a queue for the sink
        queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_SIZE)
        # add the sink data to the DataSet
        sink_dict = {
            'task': task,
            'sock': sock,
            'queue': queue,
        }
        self.sinks[sink_id] = sink_dict
        # push the full current data to the sink so it has a starting point
        queue.put_nowait(self.pickle_diff)
        await task

    async def run_source(self, sock: _CustomSock):
        """Run a data source until it closes."""
        task = asyncio.create_task(self._source_coro())
        self.source = {'task': task, 'sock': sock}
        await task

    async def _source_coro(self):
        """Receive data from a source client and transfer it to the sink client
        queues."""
        sock = self.source['sock']
        # reset the PickleDiff since there is a new source
        self.pickle_diff = PickleDiff()
        try:
            while True:
                try:
                    new_data = await asyncio.wait_for(sock.recv_msg(), timeout=_TIMEOUT)
                except (asyncio.IncompleteReadError, asyncio.TimeoutError) as exc:
                    # if there was a timeout / problem receiving the message
                    # the source client is dead and will be terminated
                    _logger.debug(
                        f'Source [{sock.addr}] disconnected or hasn\'t sent a '
                        'keepalive message - dropping connection.'
                    )
                    raise asyncio.CancelledError from exc

                if len(new_data):
                    _logger.debug(
                        f'Source [{sock.addr}] received pickle of '
                        f'[{len(new_data)}] bytes.'
                    )
                    # deserialize the PickleDiff
                    new_pickle_diff = deserialize_pickle_diff(new_data)
                    # combine the new pickle diff with what is stored on the server
                    self.pickle_diff.squash(new_pickle_diff)
                    for sink_id in self.sinks:
                        sink = self.sinks[sink_id]
                        queue = sink['queue']
                        try:
                            queue.put_nowait(new_pickle_diff)
                        except asyncio.QueueFull:
                            # the sink isn't consuming data fast enough
                            _logger.debug(
                                f'Sink [{sink["sock"].addr}] can\'t keep up '
                                'with data source.'
                            )
                            if not _squash_pickle_diff_queue(queue, new_pickle_diff):
                                _logger.warning(
                                    f'Cancelling sink [{sink_id}] because the '
                                    'max diff size was exceeded. This is a '
                                    'consequence of memory build-up due to the '
                                    'sink not being able to keep up with the '
                                    'data rate. Reduce the data rate or '
                                    'increase the client processing throughput.'
                                )
                                self.sinks[sink_id]['task'].cancel()
                        _logger.debug(
                            f'Source [{sock.addr}] queued pickle for sink '
                            f'[{sink["sock"].addr}].'
                        )
                else:
                    # the server just sent a keepalive signal
                    _logger.debug(f'Source [{sock.addr}] received keepalive.')
        except asyncio.CancelledError as exc:
            raise asyncio.CancelledError from exc
        finally:
            _logger.info(f'Dropped source [{sock.addr}].')
            self.source = None

    async def _sink_coro(
        self,
        event_loop: asyncio.AbstractEventLoop,
        sink_id: tuple,
    ):
        """Receive source data from the queue"""
        sock = self.sinks[sink_id]['sock']
        queue = self.sinks[sink_id]['queue']
        try:
            while True:
                try:
                    # get pickle data from the queue
                    pickle_diff = await asyncio.wait_for(
                        queue.get(), timeout=_KEEPALIVE_TIMEOUT
                    )
                    queue.task_done()
                    _logger.debug(f'Sink [{sock.addr}] got pickle diff from queue.')
                except asyncio.TimeoutError:
                    # if there's no data available, send a keepalive message
                    _logger.debug(
                        f'Sink [{sock.addr}] no data available - sending keepalive.'
                    )
                    new_data = b''
                else:
                    new_data = serialize_pickle_diff(pickle_diff)

                try:
                    await asyncio.wait_for(
                        sock.send_msg(new_data),
                        timeout=_OPS_TIMEOUT / 4,
                    )
                    _logger.debug(
                        f'Sink [{sock.addr}] sent ' f'[{len(new_data)}] bytes.'
                    )
                except (ConnectionError, asyncio.TimeoutError) as exc:
                    _logger.info(
                        f'Sink [{sock.addr}] disconnected or isn\'t '
                        'accepting data - dropping connection.'
                    )
                    raise asyncio.CancelledError from exc
        except asyncio.CancelledError as exc:
            raise asyncio.CancelledError from exc
        finally:
            self.sinks.pop(sink_id)
            _logger.debug(f'Dropped sink [{sock.addr}].')


class DataServer:
    """
    The server has a set of DataSet objects. Each has 1 data source, and any number of
    data sinks. Pickled object data from the source is received on its socket, then
    transferred to the FIFO of every sink. The pickle is then sent out on the sink's
    socket.
    E.g.::

        self.datasets = {

        'dataset1' : _DataSet(
        socket (source) ----------> FIFO ------> socket (sink 1)
                           |
                            ------> FIFO ------> socket (sink 2)
        ),

        'dataset2' : _DataSet(
        socket (source) ----------> FIFO ------> socket (sink 1)
                           |
                            ------> FIFO ------> socket (sink 2)
                           |
                            ------> FIFO ------> socket (sink 3)
                           |
                            ------> FIFO ------> socket (sink 4)
        ),

        ... }

    """

    def __init__(self, port: int = DATASERV_PORT):
        """
        Args:
            port: TCP/IP port of the data server
        """
        self.port = port
        # a dictionary with string identifiers mapping to DataSet objects
        self.datasets: Dict[str, _DataSet] = {}
        # asyncio event loop for running all the server tasks
        # for some reason there are performance issues on windows when using the
        # ProactorEventLoop
        selector = selectors.SelectSelector()
        self.event_loop = asyncio.SelectorEventLoop(selector)

    def serve_forever(self):
        """Run the asyncio event loop - ayncio requires this be run in the main thread
        if processes are to be spawned from the event loop.
        See https://docs.python.org/3/library/asyncio-dev.html."""
        self.event_loop.set_debug(True)
        asyncio.set_event_loop(self.event_loop)
        try:
            self.event_loop.call_soon(self._main_helper)
            self.event_loop.run_forever()
        finally:
            self.event_loop.close()
            _logger.info('Data server closed.')

    def stop(self):
        """Stop the asyncio event loop."""
        if self.event_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                _cleanup_event_loop(self.event_loop), self.event_loop
            )
        else:
            raise RuntimeError('Tried stopping the data server but it isn\'t running!')

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
        _logger.info(f'Serving on {addr}.')

        async with server:
            await server.serve_forever()

    async def _negotiation(self, sock_reader, sock_writer):
        """Coroutine that determines what kind of client has connected, and deal
        with it accordingly"""

        # custom socket wrapper for sending / receiving structured messages
        sock = _CustomSock(sock_reader, sock_writer)

        _logger.info(f'New client connection from [{sock.addr}].')

        try:
            try:
                # the first message we receive from the client should identify
                # what kind of client it is
                client_type = await asyncio.wait_for(
                    sock.recv_msg(), timeout=_NEGOTIATION_TIMEOUT
                )
            except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                _logger.warning(
                    f'Connection with client [{sock.addr}] failed before it '
                    'identified itself during the negotiation phase.'
                )
                try:
                    await sock.close()
                except IOError:
                    pass
                return

            # info client
            if client_type == _NEGOTIATION_INFO:
                _logger.info(f'Client [{sock.addr}] is type [info].')
                # the client is requesting general info about the server
                # tell the client which datasets are available
                data = ','.join(list(self.datasets.keys())).encode()
                try:
                    await asyncio.wait_for(
                        sock.send_msg(data), timeout=_NEGOTIATION_TIMEOUT
                    )
                except (ConnectionError, asyncio.TimeoutError):
                    _logger.warning(
                        f'Server failed sending data to [info] client [{sock.addr}].'
                    )
                try:
                    await sock.close()
                except IOError:
                    pass
                return

            # data source client
            elif client_type == _NEGOTIATION_SOURCE:
                _logger.info(f'Client [{sock.addr}] is type [source].')
                # the client will be a data source for a dataset on the server
                # first we need know which dataset it will provide data for
                try:
                    dataset_name_bytes = await asyncio.wait_for(
                        sock.recv_msg(), timeout=_NEGOTIATION_TIMEOUT
                    )
                except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                    _logger.warning(
                        f'Failed getting the data set name from client [{sock.addr}].'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    return

                dataset_name = dataset_name_bytes.decode()

                if dataset_name not in self.datasets:
                    # create a new DataSet
                    self.datasets[dataset_name] = _DataSet()

                # the server already contains a dataset with this name
                if self.datasets[dataset_name].source:
                    # the dataset already has a source
                    _logger.warning(
                        f'Client [{sock.addr}] wants to source data for data set '
                        f'[{dataset_name}], but it already has a source - dropping '
                        'connection.'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    return
                else:
                    _logger.info(
                        f'Client [{sock.addr}] sourcing data for data set '
                        f'[{dataset_name}].'
                    )
                    # the dataset exists and it's original source is gone, so the client
                    # will act as the new source
                    await self.datasets[dataset_name].run_source(sock)

            # data sink client
            elif client_type == _NEGOTIATION_SINK:
                _logger.info(f'Client [{sock.addr}] is type [sink].')
                # get the dataset name
                try:
                    dataset_name_bytes = await asyncio.wait_for(
                        sock.recv_msg(), timeout=_NEGOTIATION_TIMEOUT
                    )
                except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                    _logger.warning(
                        f'Failed getting the data set name from client [{sock.addr}].'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    return

                dataset_name = dataset_name_bytes.decode()

                if dataset_name in self.datasets:
                    _logger.info(
                        f'Client [{sock.addr}] sinking data from data set '
                        f'[{dataset_name}].'
                    )
                    # add the client to the sinks for the requested dataset
                    await self.datasets[dataset_name].run_sink(self.event_loop, sock)
                else:
                    # the requested dataset isn't available on the server
                    _logger.warning(
                        f'Client [{sock.addr}] wants to sink data from data set '
                        f'[{dataset_name}], but it doesn\'t exist - dropping '
                        'connection.'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    return
            # unknown client type
            else:
                # the client gave an invalid connection type
                _logger.error(
                    f'Client [{sock.addr}] provided an invalid connection type '
                    f'[{client_type}] - dropping connection.'
                )
                try:
                    await sock.close()
                except IOError:
                    pass
                return
        except ConnectionResetError:
            _logger.debug(f'Client [{sock.addr}] forcibly closed - closing connection.')
        except asyncio.CancelledError as exc:
            _logger.debug(
                f'Communication with client [{sock.addr}] cancelled - closing '
                'connection.'
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
