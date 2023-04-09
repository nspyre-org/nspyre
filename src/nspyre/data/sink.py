import asyncio
import concurrent.futures
import logging
from typing import Any
from typing import Dict

from ._asyncio_worker import AsyncioWorker
from ._streaming_pickle import _squash_pickle_diff_queue
from ._streaming_pickle import deserialize_pickle_diff
from ._streaming_pickle import PickleDiff
from ._streaming_pickle import streaming_load_pickle_diff
from .server import _CustomSock
from .server import _FAST_TIMEOUT
from .server import _NEGOTIATION_SINK
from .server import _NEGOTIATION_TIMEOUT
from .server import _QUEUE_SIZE
from .server import _TIMEOUT
from .server import DATASERV_PORT

_logger = logging.getLogger(__name__)


class DataSink(AsyncioWorker):
    """For sinking data from the :py:class:`~nspyre.data.server.DataServer`. :py:attr:`~nspyre.data.sink.DataSink.data` can be used to directly access the python object pushed by the source.
    E.g.:

    First, start the data server:

    .. code-block:: console

        $ nspyre-dataserv


    .. code-block:: python

        from nspyre import DataSink, DataSource

        with DataSource('my_dataset') as src:
            src.push('Data!')

        with DataSink('my_dataset') as sink:
            sink.pop()
            print(sink.data)

    Alternatively, if the data pushed by the source is a dictionary, its values can be accessed as if they were attributes of the sink, e.g.:

    .. code-block:: python

        from nspyre import DataSink, DataSource

        with DataSource('my_dataset') as src:
            data = {
                'some_data': 1,
                'some_other_data': 'a string'
            }
            src.push(data)

        with DataSink('my_dataset') as sink:
            sink.pop()
            print(sink.some_data)
            print(sink.some_other_data)

    """

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
        self.data: Any = None
        """The object pushed by the :py:class:`~nspyre.data.source.DataSource`."""

        # store the streaming objects
        self.streaming_obj_db: Dict[str, Any] = {}
        # IP address of the data server to connect to
        self._addr = addr
        # port of the data server to connect to
        self._port = port
        # whether the sink should try to reconnect to the data server
        self._auto_reconnect = auto_reconnect

    def connect(self):
        """Connect to the data server."""
        # do this just to generate docs
        super().connect()

    def disconnect(self):
        """Disconnect from the data server."""
        # do this just to generate docs
        super().disconnect()

    async def _main(self):
        """asyncio main loop"""
        try:
            # asyncio queue for buffering data from the server
            self._queue = asyncio.Queue(maxsize=_QUEUE_SIZE)

            while True:
                try:
                    # connect to the data server
                    sock_reader, sock_writer = await asyncio.wait_for(
                        asyncio.open_connection(self._addr, self._port),
                        timeout=_NEGOTIATION_TIMEOUT,
                    )
                except OSError as err:
                    _logger.warning(
                        f'sink failed connecting to data server [{(self._addr, self._port)}]'
                    )
                    await asyncio.sleep(_FAST_TIMEOUT)
                    if self._auto_reconnect:
                        continue
                    else:
                        raise ConnectionError(
                            f'Failed connecting to data server [{(self._addr, self._port)}]'
                        ) from err

                sock = _CustomSock(sock_reader, sock_writer)
                _logger.info(f'sink connected to data server [{sock.addr}]')

                try:
                    # notify the server that this is a data sink client
                    await asyncio.wait_for(
                        sock.send_msg(_NEGOTIATION_SINK),
                        timeout=_NEGOTIATION_TIMEOUT,
                    )
                    # send the dataset name
                    await asyncio.wait_for(
                        sock.send_msg(self._name.encode()),
                        timeout=_NEGOTIATION_TIMEOUT,
                    )
                except (ConnectionError, asyncio.TimeoutError) as err:
                    _logger.warning(
                        f'sink failed negotiation process with data server [{sock.addr}] - attempting reconnect'
                    )
                    try:
                        await sock.close()
                    except IOError:
                        pass
                    await asyncio.sleep(_FAST_TIMEOUT)
                    if self._auto_reconnect:
                        continue
                    else:
                        raise ConnectionError(
                            f'Failed connecting to data server [{(self._addr, self._port)}]'
                        ) from err

                _logger.debug(
                    f'sink finished negotiation with data server [{sock.addr}]'
                )

                # connection succeeded, so trigger the main thread to continue execution
                self._sem.release()

                while True:
                    try:
                        # get data from the server
                        new_data = await asyncio.wait_for(
                            sock.recv_msg(), timeout=_TIMEOUT
                        )
                    except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                        # if there was a timeout / problem receiving the message the data server / connection is dead
                        _logger.info(
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

                    _logger.debug(
                        f'sink received pickle of [{len(new_data)}] bytes from data server [{sock.addr}]'
                    )

                    pickle_diff = deserialize_pickle_diff(new_data)

                    try:
                        # if the server doesn't have any real data yet, ignore the first pop
                        if pickle_diff.pkl != b'':
                            # put pickle on the queue
                            self._queue.put_nowait(pickle_diff)
                    except asyncio.QueueFull as err:
                        # the user isn't consuming data fast enough so we will empty the queue and place only this most recent pickle on it
                        _logger.debug(
                            'pop() isn\'t being called frequently enough to keep up with data source'
                        )
                        if not _squash_pickle_diff_queue(self._queue, pickle_diff):
                            raise RuntimeError(
                                'Maximum diff size exceeded. \
                                This is a consequence of memory build-up due \
                                to the sink not being able to keep up with \
                                the data rate. Reduce the data rate or \
                                increase the client processing throughput.'
                            ) from err
                    _logger.debug(f'sink queued pickle of [{len(new_data)}] bytes')
                await asyncio.sleep(_FAST_TIMEOUT)

        except ConnectionError as err:
            self._exc = err
            # release the main thread if there's a connection error
            self._sem.release()
        except asyncio.CancelledError as err:
            _logger.debug(
                f'sink stopped, closing connection with data server [{sock.addr}]'
            )
            try:
                await sock.close()
            except (IOError, NameError):
                # socket is broken or hasn't been created yet
                pass
            raise err

    async def _pop(self, timeout) -> PickleDiff:
        """Coroutine that gets data from the queue."""
        try:
            # get pickle data from the queue
            pickle_diff = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.exceptions.CancelledError:
            _logger.debug('pop cancelled')
            return PickleDiff()
        except asyncio.exceptions.TimeoutError as err:
            raise TimeoutError('pop timed out') from err
        else:
            self._queue.task_done()
            return pickle_diff

    def pop(self, timeout=None):
        """Block waiting for an updated version of the data from the data
        server. Once the data is received, the internal :py:attr:`~nspyre.data.sink.DataSink.data` attribute
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
                        sink.pop():
                        # sink.freq and sink.volts have been modified
                        # replot the data to show the new values
                        my_plot_update(sink.freq, sink.volts)

        Args:
            timeout: Time to wait for an update in seconds. Set to :code:`None` to wait forever.

        Raises:
            TimeoutError: A timeout occured.
            RuntimeError: The sink isn't properly initialized.
        """
        if not self.is_running():
            raise RuntimeError(
                f'Tried to pop from data sink {self} but the sink has not been started.'
            )

        # get the most recent pickle from the queue
        future = asyncio.run_coroutine_threadsafe(self._pop(timeout), self._event_loop)
        # whether timeout ocurred
        timed_out = False

        try:
            # wait for the coroutine to return
            pickle_diff = future.result()
        except TimeoutError:
            timed_out = True
        except concurrent.futures.CancelledError:
            _logger.debug('_pop was cancelled')
        else:
            _logger.debug('pop returning new data')
            # update data object
            if pickle_diff.pkl != b'':
                self.data = streaming_load_pickle_diff(
                    self.streaming_obj_db, pickle_diff
                )
            else:
                # no data due to a timeout
                timed_out = True

        if timed_out:
            _logger.debug('pop timed out, cancelling future')
            future.cancel()
            raise TimeoutError(f'{self} pop() timed out.')

        self._check_exc()

    def __str__(self):
        return f'Data Sink (running={self.is_running()}) [name={self._name}, ip={self._addr}, port={self._port}, auto_reconnect={self._auto_reconnect}]'

    def __getattr__(self, attr: str):
        """Allow the user to access the data objects using sink.obj notation if self.data is a dictionary"""
        try:
            if attr in self.data:
                return self.data[attr]
            else:
                # raise the default python error when an attribute isn't found
                return self.__getattribute__(attr)
        except TypeError:
            # data is not iterable
            return self.__getattribute__(attr)
