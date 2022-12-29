"""For sourcing data to the data server."""

import asyncio
import concurrent.futures
import logging
import pickle

from .asyncio_worker import AsyncioWorker
from .dataserv import _CustomSock
from .dataserv import _queue_flush_and_put
from .dataserv import DATASERV_PORT
from .dataserv import FAST_TIMEOUT
from .dataserv import KEEPALIVE_TIMEOUT
from .dataserv import NEGOTIATION_SOURCE
from .dataserv import NEGOTIATION_TIMEOUT
from .dataserv import OPS_TIMEOUT
from .dataserv import QUEUE_SIZE

logger = logging.getLogger(__name__)


def _serialize(obj) -> bytes:
    """Serialize a python object into a byte stream."""
    return pickle.dumps(obj)


class DataSource(AsyncioWorker):
    """For sourcing data to the data server. See DataSink.pop() for typical usage example."""

    def __init__(
        self,
        name: str,
        addr: str = 'localhost',
        port: int = DATASERV_PORT,
        auto_reconnect: bool = False,
    ):
        """
        Args:
            name: Name of the data set.
            addr: Network address of the data server.
            port: Port of the data server.
            auto_reconnect: If True, automatically reconnect to the data
                server if it is disconnected. Otherwise raise an error if
                connection fails.
        """
        super().__init__()
        # name of the dataset
        self._name = name
        # IP address of the data server to connect to
        self._addr = addr
        # port of the data server to connect to
        self._port = port
        # whether the source should try to reconnect to the data server
        self._auto_reconnect = auto_reconnect

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

                sock = _CustomSock(sock_reader, sock_writer)
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
                _queue_flush_and_put(self._queue, new_pickle)
            logger.debug(f'source queued pickle of [{len(new_pickle)}] bytes')
        except asyncio.CancelledError:
            logger.debug('source push cancelled')
            raise

    def push(self, data):
        """Push new data to the data server.

        Args:
            data: Any python object (must be pickleable) to send. Ideally, \
                this should be a dictionary to allow for simple attribute access \
                from the sink side like :code:`sink.my_var`.
        """
        # serialize the objects
        new_pickle = _serialize(data)
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

    def __str__(self):
        return f'Data Source (running={self.is_running()}) [name={self._name}, ip={self._addr}, port={self._port}, auto_reconnect={self._auto_reconnect}]'
