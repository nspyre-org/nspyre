import logging
import queue
from functools import partial
from importlib import reload
from multiprocessing import Queue
from types import ModuleType
from typing import Optional

from pyqtgraph.Qt import QtWidgets

from ...misc.misc import ProcessRunner
from ...misc.misc import run_experiment
from .params import ParamsWidget


class ExperimentWidget(QtWidgets.QWidget):
    """Qt widget for automatically generating a GUI for a simple experiment.
    Parameters can be entered by the user in a
    :py:class:`~nspyre.gui.widgets.params.ParamsWidget`. Buttons are
    generated for the user to run, stop, and kill the experiment process.
    """

    def __init__(
        self,
        params_config: dict,
        module: ModuleType,
        cls: str,
        fun_name: str,
        constructor_args: Optional[list] = None,
        constructor_kwargs: Optional[dict] = None,
        fun_args: Optional[list] = None,
        fun_kwargs: Optional[dict] = None,
        title: Optional[str] = None,
        kill: bool = False,
        layout: QtWidgets.QLayout = None,
    ):
        """
        Args:
            params_config: Dictionary that is passed to the constructor of
                :py:class:`~nspyre.gui.widgets.params.ParamsWidget`.
            module: Python module that contains cls.
            cls: Python class name as a string. An instance of this class will
                be created in a subprocess when the user presses the 'Run' button.
                The :code:`__enter__` and :code:`__exit__` methods will be called
                if implemented. In addition, if the class constructor takes
                keyword arguments :code:`queue_to_exp` and/or :code:`queue_from_exp`,
                multiprocessing :code:`Queue` objects will be passed in that can
                be used to communicate with the GUI.
            fun_name: Name of function within cls to run. All of the values from
                the ParamsWidget will be passed as keyword arguments to this function.
            constructor_args: Args to pass to cls.
            constructor_kwargs: Keyword arguments to pass to cls.
            fun_args: Args to pass to :code:`cls.fun`.
            fun_kwargs: Keyword arguments to pass to :code:`cls.fun`.
            title: Window title.
            kill: Add a kill button to allow the user to forcibly kill the subprocess
                running the experiment function.
            layout: Additional Qt layout to place between the parameters and
                run/stop/kill buttons.
        """
        super().__init__()

        if title is not None:
            self.setWindowTitle(title)

        self.module = module
        self.cls = cls
        self.fun_name = fun_name
        if constructor_args is not None:
            self.constructor_args = constructor_args
        else:
            self.constructor_args = []

        if constructor_kwargs is not None:
            self.constructor_kwargs = constructor_kwargs
        else:
            self.constructor_kwargs = {}

        if fun_args is not None:
            self.fun_args = fun_args
        else:
            self.fun_args = []

        if fun_kwargs is not None:
            self.fun_kwargs = fun_kwargs
        else:
            self.fun_kwargs = {}

        self.params_widget = ParamsWidget(params_config)

        # run button
        run_button = QtWidgets.QPushButton('Run')
        self.run_proc = ProcessRunner()
        run_button.clicked.connect(self.run)

        self.queue_to_exp: Queue = Queue()
        """multiprocessing Queue to pass to the experiment subprocess and use
        for sending messages to the subprocess."""
        self.queue_from_exp: Queue = Queue()
        """multiprocessing Queue to pass to the experiment subprocess and use
        for receiving messages from the subprocess."""

        # notes area
        notes_label = QtWidgets.QLabel('Notes')
        self.notes_textbox = QtWidgets.QTextEdit('')

        # stop button
        stop_button = QtWidgets.QPushButton('Stop')
        stop_button.clicked.connect(self.stop)
        # use a partial because the stop function may already be destroyed by the time
        # this is called
        self.destroyed.connect(partial(self.stop, log=False))

        # kill button
        if kill:
            kill_button = QtWidgets.QPushButton('Kill')
            kill_button.clicked.connect(self.kill)

        # Qt layout that arranges the params and button vertically
        params_layout = QtWidgets.QVBoxLayout()
        params_layout.addWidget(self.params_widget)
        if layout is not None:
            params_layout.addLayout(layout)
        params_layout.addWidget(notes_label)
        params_layout.addWidget(self.notes_textbox)
        params_layout.addWidget(run_button)
        params_layout.addWidget(stop_button)
        if kill:
            params_layout.addWidget(kill_button)

        self.setLayout(params_layout)

    def run(self):
        """Run the experiment function in a subprocess."""

        if self.run_proc.running():
            logging.info(
                'Not starting the experiment process because it is still running.'
            )
            return

        # reload the module at runtime in case any changes were made to the code
        reload(self.module)
        # get the experiment class
        exp_cls = getattr(self.module, self.cls)
        # add the queues to the constructor kwargs
        constructor_kwargs = dict(
            **self.constructor_kwargs,
            queue_to_exp=self.queue_to_exp,
            queue_from_exp=self.queue_from_exp,
        )
        # add the params and notes to the function kwargs
        fun_kwargs = dict(
            **self.fun_kwargs,
            **self.params_widget.all_params(),
            notes=self.notes_textbox.toPlainText(),
        )
        # call the function in a new process
        self.run_proc.run(
            run_experiment,
            exp_cls=exp_cls,
            fun_name=self.fun_name,
            constructor_args=self.constructor_args,
            constructor_kwargs=constructor_kwargs,
            fun_args=self.fun_args,
            fun_kwargs=fun_kwargs,
        )

    def stop(self, log: bool = True):
        """Request the experiment subprocess to stop by sending the string :code:`stop`
        to :code:`queue_to_exp`.

        Args:
            log: if True, log when stop is called but the process isn't running.
        """
        if self.run_proc.running():
            self.queue_to_exp.put('stop')
        else:
            if log:
                logging.info(
                    'Not stopping the experiment process because it is not running.'
                )

    def kill(self):
        """Kill the experiment subprocess."""
        if self.run_proc.running():
            self.run_proc.kill()
        else:
            logging.info(
                'Not killing the experiment process because it is not running.'
            )


def experiment_widget_process_queue(msg_queue) -> Optional[str]:
    """Reads messages sent/received to/from a multiprocessing :code:`Queue` by \
    :py:class:`~nspyre.gui.widgets.experiment.ExperimentWidget`.

    Args:
        msg_queue: multiprocessing Queue object.

    Returns:
        The message received from the experiment subprocess.
    """
    # check for messages from the GUI
    if msg_queue is not None:
        try:
            # try to get a message from the queue
            o = msg_queue.get_nowait()
        except queue.Empty:
            # no message was available so we can continue
            return None
        else:
            return o
    else:
        return None
