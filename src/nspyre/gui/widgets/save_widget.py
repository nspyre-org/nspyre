"""
A widget to save data from the dataserver.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import json
import pickle
from pathlib import Path

from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

from ...dataserv.dataserv import DataSink

HOME = Path.home()


def save_json(filename, data):
    """Save data a json file."""
    with open(filename, 'w') as f:
        json.dump(data, f)


def save_pickle(filename, data):
    """Save data a python pickle file."""
    with open(filename, 'wb') as f:
        pickle.dump(data, f)


class SaveWidget(QWidget):
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
            'pickle': save_pickle,
            'json': save_json,
        }
        # merge with the user-provided dictionary
        if additional_filetypes:
            self.filetypes.update(additional_filetypes)

        # label for data set lineedit
        dataset_label = QLabel('Data Set')
        # text box for the user to enter the name of the desired data set in the dataserver
        self.dataset_lineedit = QLineEdit()
        dataset_layout = QHBoxLayout()
        dataset_layout.addWidget(dataset_label)
        dataset_layout.addWidget(self.dataset_lineedit)
        # dummy widget containing the data set lineedit and label
        dataset_container = QWidget()
        dataset_container.setLayout(dataset_layout)

        # dropdown menu for selecting the desired filetype
        self.filetype_combobox = QComboBox()
        self.filetype_combobox.addItems(list(self.filetypes))

        # save button
        save_button = QPushButton('Save')
        # run the relevant save method on button press
        save_button.clicked.connect(self.save)

        layout = QVBoxLayout()
        layout.addWidget(dataset_container)
        layout.addWidget(self.filetype_combobox)
        layout.addWidget(save_button)
        self.setLayout(layout)

    def save(self):
        """Save the data to a file."""
        # get the file type
        filetype = self.filetype_combobox.itemText(
            self.filetype_combobox.currentIndex()
        )
        # make a file browser dialog to get the desired file location from the user
        filename, _ = QFileDialog.getSaveFileName(
            parent=self, directory=str(self.save_dialog_dir)
        )
        if filename:
            # TODO exit gracefully if the sink doesn't immediately connect
            # connect to the dataserver
            with DataSink(self.dataset_lineedit.text()) as sink:
                # get the data from the dataserver
                if sink.pop():
                    # run the relevant save function
                    save_fun = self.filetypes[filetype]
                    save_fun(filename, sink.data)
