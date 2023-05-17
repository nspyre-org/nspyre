import logging
import time
from typing import Callable

from pyqtgraph.Qt import QtCore

from ..threadsafe import QThreadSafeObject

_logger = logging.getLogger(__name__)


class UpdateLoop(QThreadSafeObject):
    """Runs a function repeatedly in a new thread."""

    updated = QtCore.Signal()
    """Qt Signal emitted when the update function finished."""

    def __init__(
        self,
        update_func: Callable,
        *args,
        report_fps: bool = False,
        fps_period: float = 1,
        **kwargs,
    ):
        """
        Args:
            update_func: Function to run repeatedly.
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function.
            report_fps: Whether to log the frames-per-second (how many times
                update_func is running per second).
            fps_period: How often (s) to report the frames-per-second.
        """
        super().__init__()

        self.update_func = update_func
        self.args = args
        self.kwargs = kwargs
        self.running = False

        self.report_fps = report_fps
        self.fps_period = fps_period
        # keep track of how many times self._update is called in the fps_period
        self.fps_counter = 0
        # time since the last reporting of the plot update FPS
        self.last_fps = time.time()
        self.updated.connect(self._calc_fps)
        self.run_safe(self._update)

    def start(self):
        """Start the update loop."""
        super().start()
        self.running = True
        self.run_safe(self._update)

    def stop(self):
        """Stop the update loop. Block until the most recent update has finished."""
        self.running = False
        super().stop()

    def _update(self):
        """Function that runs update_func, and keeps track of the fps."""
        # exit if stop has been requested
        if not self.running:
            return

        # run the update function
        self.update_func(*self.args, **self.kwargs)

        # notify that update_func has finished
        self.updated.emit()

        # queue up another update
        self.run_safe(self._update)

    def _calc_fps(self):
        """Calculate and report how many times per second update_func is being
        called."""
        if self.report_fps:
            self.fps_counter += 1
            now = time.time()
            # time difference since last FPS report
            td = now - self.last_fps
            if td > self.fps_period:
                fps = self.fps_counter / td
                _logger.debug(f'plotting FPS: {fps:0.3f}')
                self.last_fps = now
                self.fps_counter = 0
