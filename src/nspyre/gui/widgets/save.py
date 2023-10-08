import logging
from functools import partial
from pathlib import Path
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Union

from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

from ...data.save import save_json
from ...data.save import save_pickle
from ...data.sink import DataSink
from ..threadsafe import QThreadSafeObject

_HOME = Path.home()
_logger = logging.getLogger(__name__)


class _DataSaver(QThreadSafeObject):
    """Helper for SaveWidget."""

    def save(
        self,
        filename: Union[str, Path],
        dataset: str,
        save_fun: Callable,
        timeout: Optional[float] = None,
        callback: Optional[Callable] = None,
    ):
        """
        Args:
            filename: The file to save data to.
            dataset: Data set on the data server to pull the data from.
            save_fun: Function that saves the data to a file. It should have
                the signature :code:`save(filename: Union[str, Path], data: Any)`.
            callback: Callback function to run (blocking, in the main thread)
                after the data is saved.
        """
        self.run_safe(
            self._save,
            filename=filename,
            dataset=dataset,
            save_fun=save_fun,
            timeout=timeout,
            callback=callback,
        )

    def _save(
        self,
        filename: Union[str, Path],
        dataset: str,
        save_fun: Callable,
        timeout: Optional[float] = None,
        callback: Optional[Callable] = None,
    ):
        """See save()."""
        try:
            try:
                # connect to the dataserver
                with DataSink(dataset) as sink:
                    # get the data from the dataserver
                    sink.pop(timeout=timeout)
                    save_fun(filename, sink.data)
            except TimeoutError as err:
                raise TimeoutError(
                    f'Timed out retreiving the data set [{dataset}] from data server.'
                ) from err
            else:
                _logger.info(f'Saved data set [{dataset}] to [{filename}].')
        except Exception as err:
            raise err
        finally:
            if callback is not None:
                self.run_main(callback, blocking=True)


class SaveWidget(QtWidgets.QWidget):
    """Qt widget that saves data from the :py:class:`~nspyre.data.server.DataServer` \
    to a file."""

    def __init__(
        self,
        timeout: float = 30,
        additional_filetypes: Optional[Dict[str, Callable]] = None,
        save_dialog_dir: Optional[Union[str, Path]] = None,
    ):
        """
        Args:
            timeout: Timeout for data sink pop().
            additional_filetypes: Dictionary containing string keys that
                represent a file type mapping to a tuple. The first element of the tuple
                is a list which contains the possible file extensions for the file type.
                The second element is a function that will save data to a file using the
                associated file type. E.g.:
                :code:`{'FileType': (['.jpg', '.jpeg'], save_fun)} 
                Functions should have the signature:
                :code:`save_fun(filename: str, data: Any)`.
            save_dialog_dir: Directory where the file dialog begins. If
                :code:`None`, default to the user home directory.
        """
        super().__init__()

        # helper to run the saving in a new thread
        self.saver = _DataSaver()
        self.destroyed.connect(partial(self._stop))
        self.saver.start()

        self.timeout = timeout

        if save_dialog_dir is None:
            self.save_dialog_dir: Union[str, Path] = _HOME
        else:
            self.save_dialog_dir = save_dialog_dir

        # file type options for saving data
        self.filetypes = {
            # name: (['file extension 2', 'file extension 2', ... ], save_function)
            'Pickle': (['.pickle', '.pkl'], save_pickle),
            'JSON': (['.json'], save_json),
            # TODO
            # 'Pickle (*.pickle *.pkl)': save_pickle,
            # 'JSON (*.json)': save_json,
        }
        # merge with the user-provided dictionary
        if additional_filetypes:
            self.filetypes.update(additional_filetypes)

        # generate a list of filetypes of the form:
        # ['JSON (*.json)', 'Pickle (*.pickle *.pkl)', ...]
        self.filetype_filters = []
        for filetype in self.filetypes:
            # add the file type name
            filter_str = filetype + ' ('
            # add all of the extensions
            for i, ext in enumerate(self.filetypes[filetype][0]):
                if i:
                    filter_str += ' *' + ext
                else:
                    filter_str += '*' + ext
            filter_str += ')'
            self.filetype_filters.append(filter_str)

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

        # save button
        self.save_button = QtWidgets.QPushButton('Save')
        # run the relevant save method on button press
        self.save_button.clicked.connect(self._save_clicked)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(dataset_container)
        layout.addWidget(self.save_button)
        layout.addStretch()
        self.setLayout(layout)

    def _stop(self):
        self.saver.stop()

    def _save_clicked(self):
        """Save the data to a file."""

        # data set name
        dataset = self.dataset_lineedit.text()

        # make a file browser dialog to get the desired file location from the user
        filename, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            directory=str(self.save_dialog_dir / f'{dataset}'),
            filter=';;'.join(self.filetype_filters),
        )

        if filename == '':
            # the user cancelled
            return

        # determine the selected file type
        selected_file_type = selected_filter.split(' ')[0]
        extensions = self.filetypes[selected_file_type][0]
        # add an extension if the user didn't provide it already
        if not any(ext in filename for ext in extensions):
            filename += extensions[0]

        # run the relevant save function
        save_fun = self.filetypes[selected_file_type][1]

        # run the saving in a new thread
        self.saver.save(
            filename=filename,
            dataset=dataset,
            save_fun=save_fun,
            timeout=self.timeout,
            callback=self._save_callback,
        )

        # change the color to "disabled" color
        col_bg = QtGui.QColor(
            self.palette().color(QtGui.QPalette.ColorRole.AlternateBase)
        ).name()
        col_txt = QtGui.QColor(QtCore.Qt.GlobalColor.gray).name()
        self.save_button.setStyleSheet(
            f'QPushButton {{background-color: {col_bg}; color: {col_txt};}}'
        )
        # disable the button until the save finished
        self.save_button.setEnabled(False)

    def _save_callback(self):
        """Callback for saving data."""
        # reset the color
        col_bg = QtGui.QColor(
            self.palette().color(QtGui.QPalette.ColorRole.Button)
        ).name()
        col_txt = QtGui.QColor(
            self.palette().color(QtGui.QPalette.ColorRole.ButtonText)
        ).name()
        self.save_button.setStyleSheet(
            f'QPushButton {{background-color: {col_bg}; color: {col_txt};}}'
        )
        # re-enable the button
        self.save_button.setEnabled(True)
