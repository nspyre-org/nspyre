"""
A simple wrapper interface for a QThread.

Copyright (c) 2022, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging

from PySide6.QtCore import QThread

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
            args: Arguments to pass to fun.
            kwargs: Keyword arguments to pass to fun.

        Raises:
            RuntimeError: The function from a previous call is still running.

        """
        if self.thread and not self.thread.isFinished():
            raise RuntimeError('Previous function is still running.')

        logger.debug(f'Running {fun} args: {args} kwargs: {kwargs} in a new thread.')
        # creates and starts the wrapper thread
        self.thread = ContainerThread(fun, *args, **kwargs)
