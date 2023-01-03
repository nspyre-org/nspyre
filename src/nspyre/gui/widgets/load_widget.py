"""
A widget to load data from a file and push it to the :py:class:`~nspyre.data_server.data_server.DataServer`.
"""
import json
import pickle
from pathlib import Path
from typing import Any
from typing import Union

from pyqtgraph.Qt import QtWidgets

from ...data_server.data_source import DataSource

HOME = Path.home()


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


class LoadWidget(QtWidgets.QWidget):
    """Qt widget that loads data from the :py:class:`~nspyre.data_server.data_server.DataServer`."""

    def __init__(
        self, additional_filetypes=None, load_dialog_dir: Union[str, Path] = None
    ):
        """
        Args:
            additional_filetypes: Dictionary containing string keys that
                represent a file type mapping to functions that will load data to a
                file. The keys should have the form :code:`'FileType (*.extension1 *.extension2)'`,
                e.g., :code:`'Pickle (*.pickle *.pkl)"`. Functions should have the
                signature :code:`load(filename: str, data: Any)`.
            load_dialog_dir: Directory where the file dialog begins. If :code:`None`, default to the user home directory.
        """
        super().__init__()

        if load_dialog_dir is None:
            self.load_dialog_dir: Union[str, Path] = HOME
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
        # text box for the user to enter the name of the desired data set in the dataserver
        self.dataset_lineedit = QtWidgets.QLineEdit()
        self.dataset_lineedit.setMinimumWidth(150)
        dataset_layout = QtWidgets.QHBoxLayout()
        dataset_layout.addWidget(dataset_label)
        dataset_layout.addWidget(self.dataset_lineedit)
        # dummy widget containing the data set lineedit and label
        dataset_container = QtWidgets.QWidget()
        dataset_container.setLayout(dataset_layout)

        # load button
        load_button = QtWidgets.QPushButton('Load')
        # run the relevant load method on button press
        load_button.clicked.connect(self._load_clicked)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(dataset_container)
        layout.addWidget(load_button)
        layout.addStretch()
        self.setLayout(layout)

    def _load_clicked(self):
        """Load the data from a file."""

        # generate a list of filetypes of the form, e.g.:
        # 'JSON (*.json);;Pickle (*.pickle *.pkl);; ...'
        filters = ';;'.join(self.filetypes)

        # make a file browser dialog to get the desired file location from the user
        filename, selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, directory=str(self.load_dialog_dir), filter=filters
        )

        if filename == '':
            # the user cancelled
            return

        dataset = self.dataset_lineedit.text()
        # connect to the dataserver
        try:
            with DataSource(dataset) as source:
                # run the relevant load function
                load_fun = self.filetypes[selected_filter]
                data = load_fun(filename)
                # push the data to the dataserver
                source.push(data)
        except TimeoutError as err:
            raise RuntimeError(
                f'Failed pushing data set [{dataset}] to data server.'
            ) from err
