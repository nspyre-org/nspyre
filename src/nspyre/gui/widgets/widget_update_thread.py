"""
An implementation of QThread for nspyre.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
import time

from pyqtgraph.Qt import QtCore


logger = logging.getLogger(__name__)


# TODO this should be done with a worker object
# https://mayaposch.wordpress.com/2011/11/01/how-to-really-truly-use-qthreads-the-full-explanation/
class WidgetUpdateThread(QtCore.QThread):
    """Run update_func() repeatedly in a thread."""

    def __init__(self, update_func, report_fps=False, fps_period=1):
        super().__init__()
        self.update_func = update_func
        self.report_fps = report_fps
        self.fps_period = fps_period

    def run(self):
        """Thread entry point"""
        # keep track of how frequently update_func is called in the fps_period
        fps_counter = 0
        # time since the last reporting of the plot update FPS
        last_fps = time.time()
        while self.update_func:
            self.update_func()
            # calculate how many times per second update_func is being called
            if self.report_fps:
                fps_counter += 1
                now = time.time()
                # time difference since last FPS report
                td = now - last_fps
                if td > self.fps_period:
                    fps = fps_counter / td
                    logger.debug(f'plotting FPS: {fps:0.3f}')
                    last_fps = now
                    fps_counter = 0
