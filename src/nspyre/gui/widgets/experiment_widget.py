
import logging
from functools import partial
from importlib import reload
from multiprocessing import Queue
from types import ModuleType

from pyqtgraph.Qt import QtWidgets

from ...misc.misc import ProcessRunner
from .params_widget import ParamsWidget


class ExperimentWidget(QtWidgets.QWidget):
    """Qt widget for automatically generating a GUI for a simple experiment. 
    Parameters can be entered by the user in a 
    :py:class:`~nspyre.gui.widgets.params_widget.ParamsWidget`. Buttons are 
    generated for the user to run, stop, and kill the experiment process. The 
    keyword argument :code:`msg_queue` containing a multiprocessing Queue 
    object is passed to the function. The Queue is used to pass messages to the 
    subprocess running the experiment function. When the user presses the stop 
    button, the string :code:`stop` is pushed to the Queue.
    """

    def __init__(
        self,
        params_config: dict,
        module: ModuleType,
        cls: str,
        fun_name: str,
        args: list = None,
        kwargs: dict = None,
        title: str = None,
        kill: bool = False,
        layout: QtWidgets.QLayout = None,
    ):
        """
        Args:
            params_config: Dictionary that is passed to the constructor of
                :py:class:`~nspyre.gui.widgets.params_widget.ParamsWidget`.
            module: Python module that contains cls.
            cls: Python class name as a string (that descends from QWidget).
                An instance of this class will be created when the user tries
                to load the widget and it will be added to the pyqtgraph DockArea.
            fun_name: Name of function within cls to run.
            args: Args to pass to cls.
            kwargs: Keyword args to pass to cls.
            title: Window title.
            kill: Add a kill button to allow the user to forcibly kill the subprocess running the experiment function.
            layout: Additional Qt layout to place between the parameters and run/stop/kill buttons.
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
        if kill:
            kill_button = QtWidgets.QPushButton('Kill')
            kill_button.clicked.connect(self.kill)

        # Qt layout that arranges the params and button vertically
        params_layout = QtWidgets.QVBoxLayout()
        params_layout.addWidget(self.params_widget)
        if layout is not None:
            params_layout.addLayout(layout)
        # add stretch element to take up any extra space below the spinboxes
        params_layout.addStretch()
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

        self.queue = Queue()

        # reload the module at runtime in case any changes were made to the code
        reload(self.module)
        # get the experiment class
        exp_cls = getattr(self.module, self.cls)
        # make an instance of the experiment
        experiment = exp_cls(*self.args, **self.kwargs)
        # get the function that runs the experiment
        fun = getattr(experiment, self.fun_name)
        # call the function in a new process
        self.run_proc.run(fun, msg_queue=self.queue, **self.params_widget.all_params())

    def stop(self):
        """Stop the experiment subprocess."""
        if self.queue is not None and self.run_proc.running():
            self.queue.put('stop')
        else:
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
