"""
A widget to save data from the dataserver.
"""
import json
import pickle
from pathlib import Path

import numpy as np
from pyqtgraph.Qt import QtWidgets

from ...dataserv.dataserv import DataSink

HOME = Path.home()


class NumpyEncoder(json.JSONEncoder):
    """For converting numpy arrays to python lists so that they can be written to JSON:
    https://stackoverflow.com/questions/26646362/numpy-array-is-not-json-serializable
    """

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def save_json(filename, data):
    """Save data to a json file."""
    with open(filename, 'w') as f:
        json.dump(data, f, cls=NumpyEncoder, indent=4)


def save_pickle(filename, data):
    """Save data to a python pickle file."""
    with open(filename, 'wb') as f:
        pickle.dump(data, f)


class SaveWidget(QtWidgets.QWidget):
    """Qt widget that saves data from the dataserver."""

    def __init__(self, additional_filetypes=None, save_dialog_dir=HOME):
        """
        Args:
            additional_filetypes: Dictionary containing string key names mapping to functions that will save data to a file. The function should have the form save(filename: str, data: Any).
            save_dialog_dir: Directory where the file dialog begins.
        """
        super().__init__()

        self.save_dialog_dir = save_dialog_dir

        # file type options for saving data
        self.filetypes = {
            'json': save_json,
            'pkl': save_pickle,
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

        # dropdown menu for selecting the desired filetype
        self.filetype_combobox = QtWidgets.QComboBox()
        self.filetype_combobox.addItems(list(self.filetypes))

        # save button
        save_button = QtWidgets.QPushButton('Save')
        # run the relevant save method on button press
        save_button.clicked.connect(self.save)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(dataset_container)
        layout.addWidget(self.filetype_combobox)
        layout.addWidget(save_button)
        layout.addStretch()
        self.setLayout(layout)

    def save(self):
        """Save the data to a file."""
        # get the file type
        filetype = self.filetype_combobox.itemText(
            self.filetype_combobox.currentIndex()
        )
        # make a file browser dialog to get the desired file location from the user
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self, directory=str(self.save_dialog_dir / f'data.{filetype}')
        )
        if filename:
            dataset = self.dataset_lineedit.text()
            # connect to the dataserver
            try:
                with DataSink(dataset) as sink:
                    # get the data from the dataserver
                    if sink.pop(timeout=0.1):
                        # run the relevant save function
                        save_fun = self.filetypes[filetype]
                        save_fun(filename, sink.data)
            except TimeoutError as err:
                raise RuntimeError(
                    f'Failed getting data set [{dataset}] from data server.'
                ) from err
