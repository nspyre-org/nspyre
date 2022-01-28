"""
Some simple wrappers for running functions concurrently.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
from multiprocessing import Process

from PyQt5.QtCore import QThread

logger = logging.getLogger(__name__)


class ContainerThread(QThread):
    """Runs a function in a new QThread."""

    def __init__(self, fun, *args, **kwargs):
        super().__init__()
        self.fun = fun
        self.args = args
        self.kwargs = kwargs
        self.start()

    def run(self):
        """Thread entry point"""
        self.fun(*self.args, **self.kwargs)


class QThreadRunner:
    """Wrapper for a QThread. Input a function and arguments to be run in a separate QThread."""

    def __init__(self):
        self.thread = None

    def run(self, fun, *args, **kwargs):
        """Run the provided function in a separate thread.

        Args:
            fun: Function to run.
            args: arguments to pass to fun.
            kwargs: keyword arguments to pass to fun.

        Raises:
            RuntimeError: The function from a previous call is still running.

        """
        if self.thread and not self.thread.isFinished():
            raise RuntimeError('Previous function is still running.')

        logger.debug(f'Running {fun} args: {args} kwargs: {kwargs} in a new thread.')
        # creates and starts the wrapper thread
        self.thread = ContainerThread(fun, *args, **kwargs)


class ProcessRunner:
    """Run a function in a new process."""

    def __init__(self, kill=True):
        """
        Args:
            kill: Whether to kill a previously running process that hasn't completed.

        """
        self.proc = None
        self.should_kill = kill

    def run(self, fun, *args, **kwargs):
        """Run the provided function in a separate process.

        Args:
            fun: Function to run.
            args: arguments to pass to fun.
            kwargs: keyword arguments to pass to fun.

        Raises:
            RuntimeError: The function from a previous call is still running.

        """

        if self.proc and self.proc.is_alive():
            if self.should_kill:
                logger.debug('Previous function is still running. Killing it...')
                self.kill()
            else:
                raise RuntimeError('Previous function is still running.')

        logger.debug(f'Running process {fun} args: {args} kwargs: {kwargs}.')
        self.proc = Process(target=fun, args=args, kwargs=kwargs, daemon=True)
        self.proc.start()

    def kill(self):
        """Kill the process."""
        if self.proc:
            self.proc.terminate()
            self.proc.join()
            self.proc = None
