import asyncio
import concurrent.futures
import logging
import pickle
import selectors
from threading import Semaphore
from threading import Thread
from typing import Any
from typing import Dict

from .dataserv import _cleanup_event_loop
from .dataserv import _CustomSock
from .dataserv import _queue_flush_and_put
from .dataserv import DATASERV_PORT
from .dataserv import FAST_TIMEOUT
from .dataserv import NEGOTIATION_SINK
from .dataserv import NEGOTIATION_TIMEOUT
from .dataserv import QUEUE_SIZE
from .dataserv import TIMEOUT

logger = logging.getLogger(__name__)


def _deserialize(obj) -> Any:
    """Deserialize a python object from a byte stream."""
    return pickle.loads(obj)


class DataSink:
    """For sinking data from a data server."""

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
                _cleanup_event_loop(self._event_loop), self._event_loop
            )
        else:
            raise RuntimeError('tried stopping the data sink but it isn\'t running!')

    def _event_loop_thread(self):
        """Run the asyncio event loop - this may be run in a separate thread because
        we aren't starting any subprocesses or responding to signals"""
        logger.debug(f'started DataSource event loop thread {self._thread}')
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

                sock = _CustomSock(sock_reader, sock_writer)
                logger.info(f'sink connected to data server [{sock.addr}]')

                try:
                    # notify the server that this is a data sink client
                    await asyncio.wait_for(
                        sock.send_msg(NEGOTIATION_SINK),
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

                while True:
                    try:
                        # get data from the server
                        new_pickle = await asyncio.wait_for(
                            sock.recv_msg(), timeout=TIMEOUT
                        )
                    except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                        # if there was a timeout / problem receiving the message the data server / connection is dead
                        logger.info(
                            f'sink data server [{sock.addr}] disconnected or hasn\'t sent a keepalive message - dropping connection'
                        )
                        try:
                            await sock.close()
                        except IOError:
                            pass
                        break

                    if not new_pickle:
                        # keepalive message
                        continue

                    logger.debug(
                        f'sink received pickle of [{len(new_pickle)}] bytes from data server [{sock.addr}]'
                    )

                    try:
                        # put pickle on the queue
                        self._queue.put_nowait(new_pickle)
                    except asyncio.QueueFull:
                        # the user isn't consuming data fast enough so we will empty the queue and place only this most recent pickle on it
                        logger.debug(
                            'pop() isn\'t being called frequently enough to keep up with data source'
                        )
                        # empty the queue then put a single item into it
                        _queue_flush_and_put(self._queue, new_pickle)
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
        """Coroutine that gets data from the queue."""
        try:
            # get pickle data from the queue
            new_pickle = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.exceptions.CancelledError:
            logger.debug('pop cancelled')
            return b''
        except asyncio.exceptions.TimeoutError as err:
            raise TimeoutError('pop timed out') from err
        else:
            self._queue.task_done()
            return new_pickle

    def pop(self, timeout=None) -> bool:
        """Block waiting for an updated version of the data from the data
        server. Once the data is received, the internal data instance variable
        will be updated and the function will return.

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
            timeout: Time to wait for an update in seconds. Set to :code:`None` to wait forever.

        Raises:
            TimeoutError: A timeout occured.

        Returns:
            bool: True if successful, False otherwise.

        """
        ret = False
        # get the most recent pickle from the queue
        future = asyncio.run_coroutine_threadsafe(self._pop(timeout), self._event_loop)

        try:
            # wait for the coroutine to return
            new_pickle = future.result()
        except TimeoutError as err:
            logger.debug('pop timed out, cancelling future')
            future.cancel()
            raise err
        except concurrent.futures.CancelledError:
            logger.debug('_pop was cancelled')
        else:
            logger.debug(f'pop returning [{len(new_pickle)}] bytes unpickled')
            # update data object
            self.data = _deserialize(new_pickle)
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
