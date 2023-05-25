import json
import logging
import pickle
from functools import partial
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Union

from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

from ...data.source import DataSource
from ..threadsafe import QThreadSafeObject

_HOME = Path.home()
_logger = logging.getLogger(__name__)


def load_json(filename: Union[str, Path]) -> Any:
    """Load data from a JSON file.

    Args:
        filename: File to load from.

    Returns:
        A Python object loaded from the file.
    """
    with open(filename, 'r') as f:
        data = json.load(f)
    return data


def load_pickle(filename: Union[str, Path]) -> Any:
    """Load data from a Python pickle file.

    Args:
        filename: File to load from.

    Returns:
        A Python object loaded from the file.
    """
    with open(filename, 'rb') as f:
        data = pickle.load(f)
    return data


class _DataLoader(QThreadSafeObject):
    """Helper for LoadWidget."""

    def load(
        self,
        filename: Union[str, Path],
        dataset: str,
        load_fun: Callable,
        callback: Optional[Callable] = None,
    ):
        """
        Args:
            filename: The file to load data from.
            dataset: Data set on the data server to push the loaded data to.
            load_fun: Function that loads the data from a file. It should have
                the signature :code:`load(filename: Union[str, Path]) -> Any`.
            callback: Callback function to run (blocking, in the main thread)
                after the data is loaded.
        """
        self.run_safe(
            self._load,
            filename=filename,
            dataset=dataset,
            load_fun=load_fun,
            callback=callback,
        )

    def _load(
        self,
        filename: Union[str, Path],
        dataset: str,
        load_fun: Callable,
        callback: Optional[Callable] = None,
    ):
        """See load()."""
        # connect to the dataserver
        with DataSource(dataset) as source:
            # load data from the file
            data = load_fun(filename)
            # push the data to the dataserver
            source.push(data)
            _logger.info(f'Pushed loaded data set [{dataset}] to the data server.')
        if callback is not None:
            self.run_main(callback, blocking=True)


class LoadWidget(QtWidgets.QWidget):
    """Qt widget that loads data from a file and pushes it to the \
    :py:class:`~nspyre.data.server.DataServer`."""

    def __init__(
        self,
        additional_filetypes: Optional[Dict[str, Callable]] = None,
        load_dialog_dir: Optional[Union[str, Path]] = None,
    ):
        """
        Args:
            additional_filetypes: Dictionary containing string keys that
                represent a file type mapping to functions that will load data
                to a file. The keys should have the form
                :code:`'FileType (*.extension1 *.extension2)'`, e.g.,
                :code:`'Pickle (*.pickle *.pkl)"`. Functions should have the
                signature :code:`load(filename: Union[str, Path]) -> Any`.
            load_dialog_dir: Directory where the file dialog begins. If
                :code:`None`, default to the user home directory.
        """
        super().__init__()

        # helper to run the loading in a new thread
        self.loader = _DataLoader()
        self.destroyed.connect(partial(self._stop))
        self.loader.start()

        if load_dialog_dir is None:
            self.load_dialog_dir: Union[str, Path] = _HOME
        else:
            self.load_dialog_dir = load_dialog_dir

        # file type options for saving data
        self.filetypes = {
            'Pickle (*.pickle *.pkl)': load_pickle,
            'JSON (*.json)': load_json,
        }
        # merge with the user-provided dictionary
        if additional_filetypes:
            self.filetypes.update(additional_filetypes)

        # label for data set lineedit
        dataset_label = QtWidgets.QLabel('Data Set')
        # text box for the user to enter the name of the desired data set in
        # the dataserver
        self.dataset_lineedit = QtWidgets.QLineEdit()
        self.dataset_lineedit.setMinimumWidth(150)
        dataset_layout = QtWidgets.QHBoxLayout()
        dataset_layout.addWidget(dataset_label)
        dataset_layout.addWidget(self.dataset_lineedit)
        # dummy widget containing the data set lineedit and label
        dataset_container = QtWidgets.QWidget()
        dataset_container.setLayout(dataset_layout)

        # load button
        self.load_button = QtWidgets.QPushButton('Load')
        # run the relevant load method on button press
        self.load_button.clicked.connect(self._load_clicked)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(dataset_container)
        layout.addWidget(self.load_button)
        layout.addStretch()
        self.setLayout(layout)

    def _stop(self):
        self.loader.stop()

    def _load_clicked(self):
        """Load the data from a file."""

        # generate a list of filetypes of the form, e.g.:
        # 'JSON (*.json);;Pickle (*.pickle *.pkl);; ...'
        filters = ';;'.join(self.filetypes)

        # make a file browser dialog to get the desired file location from
        # the user
        filename, selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, directory=str(self.load_dialog_dir), filter=filters
        )

        if filename == '':
            # the user cancelled
            return

        dataset = self.dataset_lineedit.text()

        # get the relevant load function
        load_fun = self.filetypes[selected_filter]

        # run the loading in a new thread
        self.loader.load(
            filename=filename,
            dataset=dataset,
            load_fun=load_fun,
            callback=self._load_callback,
        )

        # change the color to "disabled" color
        col_bg = QtGui.QColor(
            self.palette().color(QtGui.QPalette.ColorRole.AlternateBase)
        ).name()
        col_txt = QtGui.QColor(QtCore.Qt.GlobalColor.gray).name()
        self.load_button.setStyleSheet(
            f'QPushButton {{background-color: {col_bg}; color: {col_txt};}}'
        )
        # disable the button until the load finished
        self.load_button.setEnabled(False)

    def _load_callback(self):
        """Callback for loading data."""
        # reset the color
        col_bg = QtGui.QColor(
            self.palette().color(QtGui.QPalette.ColorRole.Button)
        ).name()
        col_txt = QtGui.QColor(
            self.palette().color(QtGui.QPalette.ColorRole.ButtonText)
        ).name()
        self.load_button.setStyleSheet(
            f'QPushButton {{background-color: {col_bg}; color: {col_txt};}}'
        )
        # re-enable the button
        self.load_button.setEnabled(True)
