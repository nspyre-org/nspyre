from pathlib import Path
from typing import Any
from typing import Union

from pyqtgraph.Qt import QtWidgets

from ...data.sink import DataSink
from ...data.save import save_json
from ...data.save import save_pickle

_HOME = Path.home()


class SaveWidget(QtWidgets.QWidget):
    """Qt widget that saves data from the :py:class:`~nspyre.data.server.DataServer` to a file."""

    def __init__(
        self,
        timeout: float = 10,
        additional_filetypes: dict = None,
        save_dialog_dir: Union[str, Path] = None,
    ):
        """
        Args:
            timeout: Timeout for data sink pop().
            additional_filetypes: Dictionary containing string keys that
                represent a file type mapping to functions that will save data to a
                file. The keys should have the form :code:`'FileType (*.extension1 *.extension2)'`,
                e.g., :code:`'Pickle (*.pickle *.pkl)"`. Functions should have the
                signature :code:`save(filename: str, data: Any)`.
            save_dialog_dir: Directory where the file dialog begins. If :code:`None`, default to the user home directory.
        """
        super().__init__()

        self.timeout = timeout

        if save_dialog_dir is None:
            self.save_dialog_dir: Union[str, Path] = _HOME
        else:
            self.save_dialog_dir = save_dialog_dir

        # file type options for saving data
        self.filetypes = {
            'Pickle (*.pickle *.pkl)': save_pickle,
            'JSON (*.json)': save_json,
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

        # save button
        save_button = QtWidgets.QPushButton('Save')
        # run the relevant save method on button press
        save_button.clicked.connect(self._save_clicked)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(dataset_container)
        layout.addWidget(save_button)
        layout.addStretch()
        self.setLayout(layout)

    def _save_clicked(self):
        """Save the data to a file."""

        # generate a list of filetypes of the form, e.g.:
        # 'JSON (*.json);;Pickle (*.pickle *.pkl);; ...'
        filters = ';;'.join(self.filetypes)

        # data set name
        dataset = self.dataset_lineedit.text()

        # make a file browser dialog to get the desired file location from the user
        filename, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            directory=str(self.save_dialog_dir / f'{dataset}'),
            filter=filters,
        )

        if filename == '':
            # the user cancelled
            return

        # pick out the file extension from the filter string, e.g.
        # 'Pickle (*.pickle *.pkl)' -> '.pickle'
        extension = selected_filter.replace(' ', ')').split('*')[1].split(')')[0]
        filename += extension

        # connect to the dataserver
        try:
            with DataSink(dataset) as sink:
                # get the data from the dataserver
                sink.pop(timeout=self.timeout)
                # run the relevant save function
                save_fun = self.filetypes[selected_filter]
                save_fun(filename, sink.data)
        except TimeoutError as err:
            raise TimeoutError(
                f'Timed out retreiving the data set [{dataset}] from data server. If the data set is very large, you may need to increase the SaveWidget timeout.'
            ) from err
