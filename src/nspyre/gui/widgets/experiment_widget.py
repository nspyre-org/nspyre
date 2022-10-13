"""Widget that generates a GUI for a simple experiment with a set of
user-defined parameters and buttons to run, stop, and kill the experiment
process.

Copyright (c) 2022 Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
from functools import partial
from importlib import reload
from multiprocessing import Queue
from types import ModuleType

from pyqtgraph.Qt import QtWidgets

from ...misc.misc import ProcessRunner
from .params_widget import ParamsWidget

logger = logging.getLogger(__name__)


class ExperimentWidget(QtWidgets.QWidget):
    """Qt widget generating a GUI for a simple experiment."""

    def __init__(
        self,
        params_config: dict,
        module: ModuleType,
        cls: str,
        fun_name: str,
        args: list = None,
        kwargs: dict = None,
        title: str = None,
    ):
        """Init ExperimentWidget.

        Args:
            params_config: dictionary that is passed to the constructor of ParamsWidget. See ParamsWidget docs for details.
            module: python module that contains cls
            cls: python class name as a string (that descends from QWidget).
                An instance of this class will be created when the user tries
                to load the widget and it will be added to the DockArea.
            fun_name: name of function within cls to run
            args: args to pass to cls
            kwargs: keyword args to pass to cls
            title: window title

        """
        super().__init__()

        if title is not None:
            self.setWindowTitle(title)

        self.module = module
        self.cls = cls
        self.fun_name = fun_name
        if args is not None:
            self.args = args
        else:
            self.args = []

        if kwargs is not None:
            self.kwargs = kwargs
        else:
            self.kwargs = {}

        self.params_widget = ParamsWidget(params_config)

        # run button
        run_button = QtWidgets.QPushButton('Run')
        self.run_proc = ProcessRunner()
        run_button.clicked.connect(self.run)

        # multiprocessing queue to pass to the experiment subprocess and use for communication with the
        self.queue = None

        # stop button
        stop_button = QtWidgets.QPushButton('Stop')
        stop_button.clicked.connect(self.stop)
        # use a partial because the stop function may already be destroyed by the time this is called
        self.destroyed.connect(partial(self.stop))

        # kill button
        kill_button = QtWidgets.QPushButton('Kill')
        kill_button.clicked.connect(self.kill)

        # Qt layout that arranges the params and button vertically
        params_layout = QtWidgets.QVBoxLayout()
        params_layout.addWidget(self.params_widget)
        params_layout.addWidget(run_button)
        params_layout.addWidget(stop_button)
        params_layout.addWidget(kill_button)

        self.setLayout(params_layout)

    def run(self):
        """Run the experiment function."""

        self.queue = Queue()

        # reload the module at runtime in case any changes were made to the code
        reload(self.module)
        # make an instance of the experiment
        experiment = self.cls(*self.args, **self.kwargs)
        # get the function that runs the experiment
        fun = getattr(experiment, self.fun_name)
        # call the function in a new process
        self.run_proc.run(fun, msg_queue=self.queue, **self.params_widget.all_params())

    def stop(self):
        """Stop the sweep process."""
        if self.queue is not None and self.run_proc.running():
            self.queue.put('stop')
        else:
            logging.info(
                'Not stopping the experiment process because it is not running.'
            )

    def kill(self):
        """Kill the sweep process."""
        if self.run_proc.running():
            self.run_proc.kill()
        else:
            logging.info(
                'Not killing the experiment process because it is not running.'
            )
