""" """
import asyncio
import concurrent.futures
import logging
import selectors
import time
from threading import Semaphore
from threading import Thread

from .server import _cleanup_event_loop

_logger = logging.getLogger(__name__)


class AsyncioWorker:
    """Implements functionality for an asyncio event loop running in a separate thread."""

    def __init__(self):
        # asyncio event loop for sending/receiving data to/from the socket
        self._event_loop = None
        # store exceptions thrown in the event loop (running in another thread)
        self._exc = None
        # semaphore to block until the event loop is ready to start serving requests
        self._sem = None

    def connect(self):
        """Start the :code:`asyncio` event loop."""
        if self.is_running():
            raise RuntimeError(f'Cannot connect() because an event loop is already running.')

        selector = selectors.SelectSelector()
        self._event_loop = asyncio.SelectorEventLoop(selector)
        self._sem = Semaphore(value=0)
        # thread for running self._event_loop
        self._thread = Thread(target=self._event_loop_thread, daemon=True)
        self._thread.start()
        self._sem.acquire()
        self._check_exc()

    def disconnect(self, timeout=3):
        """Stop the :code:`asyncio` event loop.

        Args:
            timeout: time to wait to shut down the event loop.
        """
        if self.is_running():
            # wait for the queue to be empty (with timeout) to allow any pushes in the pipeline to be sent
            future = asyncio.run_coroutine_threadsafe(
                self._queue.join(), self._event_loop
            )
            # wait for the coroutine to return
            try:
                future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                _logger.info(
                    'Timed out waiting for the DataSource queue to be empty. Stopping anyway...'
                )
                future.cancel()
                return
            except concurrent.futures.CancelledError:
                logging.error('queue.join() was cancelled. This is shouldn\'t happen.')
            # kill the event loop
            asyncio.run_coroutine_threadsafe(
                _cleanup_event_loop(self._event_loop), self._event_loop
            )
        else:
            raise RuntimeError('Tried to disconnect but it isn\'t running!')

    def is_running(self):
        """Return True if the event loop is running."""
        return self._event_loop is not None and self._event_loop.is_running()

    def _event_loop_thread(self):
        """Run the asyncio event loop - this may be run in a separate thread because
        we aren't starting any subprocesses or responding to signals."""
        _logger.debug(f'started DataSource event loop thread {self._thread}')
        self._event_loop.set_debug(True)
        asyncio.set_event_loop(self._event_loop)
        try:
            self._event_loop.call_soon(self._main_helper)
            self._event_loop.run_forever()
        finally:
            self._event_loop.close()
            _logger.info(f'source [{(self._addr, self._port)}] closed')

    def _main_helper(self):
        """Callback function to start _main."""
        asyncio.create_task(self._main())

    async def _main(self):
        """Subclasses should override this."""
        while True:
            time.sleep(1)

    def _check_exc(self):
        """Check to see if an exception was raised in the event loop thread."""
        if self._exc is not None:
            raise self._exc

    def __enter__(self):
        """Python context manager setup."""
        self.connect()
        return self

    def __exit__(self, *args):
        """Python context manager teardown."""
        self.disconnect()

    def __del__(self):
        if self.is_running():
            _logger.warning(
                f'{self} event loop is still running. Did you forget to call disconnect()?'
            )
