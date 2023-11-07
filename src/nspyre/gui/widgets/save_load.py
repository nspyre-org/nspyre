import logging
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

from ...data.file import load_json
from ...data.file import load_pickle
from ...data.file import save_json
from ...data.file import save_pickle
from ...data.sink import DataSink
from ...data.source import DataSource
from ..threadsafe import QThreadSafeObject
from ..threadsafe import run_threadsafe

_HOME = Path.home()
_logger = logging.getLogger(__name__)


class _DataBackend(QThreadSafeObject):
    """Helper for SaveLoadWidget."""

    def __init__(self):
        super().__init__()
        self.data = None

    def get_all_keys(self) -> Optional[list]:
        """If the data is a dictionary, return all of its dictionary keys. Otherwise
        return None."""
        if isinstance(self.data, dict):
            return list(self.data.keys())
        else:
            return None

    @run_threadsafe(blocking=True)
    def get_key(self, key) -> Any:
        """Returns the value corresponeding to key.

        Args:
            key: The key that we will return the corresponding value for.

        """
        with QtCore.QMutexLocker(self.mutex):
            try:
                return self.data[key]
            except Exception as err:
                raise err
            else:
                _logger.info(f'Got key [{key}].')

    @run_threadsafe()
    def set_key(self, key, val, callback: Optional[Callable] = None):
        """Sets the value corresponeding to key.

        Args:
            key: The key that we will set the value for.
            value: The value to assign to key.
            callback: Callback function to run (blocking, in the main thread)
                after this function.

        """
        with QtCore.QMutexLocker(self.mutex):
            self.data[key] = val
            _logger.info(f'Set key [{key}] = [{val}].')
            if callback is not None:
                self.run_main(callback, self.get_all_keys(), blocking=True)

    @run_threadsafe()
    def del_key(self, key: str, callback: Optional[Callable] = None):
        """Delete the key.

        Args:
            key: The key that will be deleted.
            callback: Callback function to run (blocking, in the main thread)
                after this function.

        """
        with QtCore.QMutexLocker(self.mutex):
            try:
                del self.data[key]
            except Exception as err:
                raise err
            else:
                _logger.info(f'Deleted key [{key}].')
            finally:
                if callback is not None:
                    self.run_main(callback, self.get_all_keys(), blocking=True)

    @run_threadsafe()
    def push(
        self,
        dataset: str,
        callback: Optional[Callable] = None,
    ):
        """
        Args:
            dataset: Data set on the data server to push the data to.
            callback: Callback function to run (blocking, in the main thread)
                after this function.
        """
        with QtCore.QMutexLocker(self.mutex):
            try:
                if self.data is None:
                    raise RuntimeError(
                        f'Cannot push data to data set [{dataset}] '
                        'because no data is loaded.'
                    )
                with DataSource(dataset) as source:
                    # push the data to the dataserver
                    source.push(self.data)
            except Exception as err:
                raise err
            else:
                _logger.info(f'Pushed data set [{dataset}] to the data server.')
            finally:
                if callback is not None:
                    self.run_main(callback, blocking=True)

    @run_threadsafe()
    def pop(
        self,
        dataset: str,
        timeout: Optional[float] = None,
        callback: Optional[Callable] = None,
    ):
        """
        Args:
            dataset: Data set on the data server to pop the data from.
            timeout: Max time to wait for pop operation.
            callback: Callback function to run (blocking, in the main thread)
                after this function.
        """
        with QtCore.QMutexLocker(self.mutex):
            try:
                try:
                    # connect to the dataserver
                    with DataSink(dataset) as sink:
                        # get the data from the dataserver
                        sink.pop(timeout=timeout)
                        self.data = sink.data
                except TimeoutError as err:
                    raise TimeoutError(
                        f'Timed out retreiving the data set [{dataset}] from data '
                        'server.'
                    ) from err
                else:
                    _logger.info(f'Popped data set [{dataset}].')
            except Exception as err:
                raise err
            finally:
                if callback is not None:
                    self.run_main(callback, self.get_all_keys(), blocking=True)

    @run_threadsafe()
    def save(
        self,
        filename: Union[str, Path],
        save_fun: Callable,
        callback: Optional[Callable] = None,
    ):
        """
        Args:
            filename: The file to save data to.
            save_fun: Function that saves the data to a file. It should have
                the signature :code:`save(filename: Union[str, Path], data: Any)`.
            callback: Callback function to run (blocking, in the main thread)
                after this function.
        """
        with QtCore.QMutexLocker(self.mutex):
            if self.data is None:
                raise RuntimeError(
                    f'Cannot save data to [{filename}] ' 'because no data is loaded.'
                )
            try:
                save_fun(filename, self.data)
            except Exception as err:
                raise err
            else:
                _logger.info(f'Saved data to [{filename}].')
            finally:
                if callback is not None:
                    self.run_main(callback, blocking=True)

    @run_threadsafe()
    def load(
        self,
        filename: Union[str, Path],
        load_fun: Callable,
        callback: Optional[Callable] = None,
    ):
        """
        Args:
            filename: The file to load data from.
            load_fun: Function that loads the data from a file. It should have
                the signature :code:`load(filename: Union[str, Path]) -> Any`.
            callback: Callback function to run (blocking, in the main thread)
                after this function.
        """
        with QtCore.QMutexLocker(self.mutex):
            try:
                self.data = load_fun(filename)
            except Exception as err:
                raise err
            else:
                _logger.info(f'Loaded data set from file [{filename}].')
            finally:
                if callback is not None:
                    self.run_main(callback, self.get_all_keys(), blocking=True)


class SaveLoadWidget(QtWidgets.QWidget):
    """Qt widget that transfers data (with optional modifications) between the
    :py:class:`~nspyre.data.server.DataServer` and files."""

    def __init__(
        self,
        timeout: float = 30,
        file_dialog_dir: Optional[Union[str, Path]] = None,
        additional_filetypes: Optional[
            Dict[str, tuple[list, Callable, Callable]]
        ] = None,
    ):
        """
        Args:
            timeout: Timeout for data sink pop().
            file_dialog_dir: Directory where the file dialog begins. If
                :code:`None`, default to the user home directory.
            additional_filetypes: Dictionary containing string keys that
                represent a file type mapping to a tuple. The first element of the tuple
                is a list which contains the possible file extensions for the file type.
                The second element is a function that will save data to a file using the
                associated file type. The save function should have the signature:
                :code:`save_fun(filename: str, data: Any)`.
                The third element is a function that will load data from a file using
                the associated file type. The load function should have the signature:
                :code:`load(filename: Union[str, Path]) -> Any`. E.g.:
                :code:`{'FileType': (['.jpg', '.jpeg'], save_fun, load_fun)}`
        """
        super().__init__()

        self.timeout = timeout

        if file_dialog_dir is None:
            # set the default file dialog path
            self.file_dialog_dir: Union[str, Path] = _HOME
        else:
            if isinstance(self.file_dialog_dir, Path):
                self.file_dialog_dir = file_dialog_dir
            else:
                self.file_dialog_dir = Path(file_dialog_dir)

        # file type options for saving data
        self.filetypes = {
            # name: (['file ext 2', 'file ext 2', ... ], save_fun, load_fun)
            'Pickle': (['.pickle', '.pkl'], save_pickle, load_pickle),
            'JSON': (['.json'], save_json, load_json),
        }
        # merge with the user-provided dictionary
        if additional_filetypes:
            self.filetypes.update(additional_filetypes)

        # generate a list of save filetypes of the form:
        # ['JSON (*.json)', 'Pickle (*.pickle *.pkl)', ...]
        self.browse_filetype_filters = []
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
            self.browse_filetype_filters.append(filter_str)

        # helper to run the saving in a new thread
        self.backend = _DataBackend()
        self.destroyed.connect(partial(self._stop))
        self.backend.start()

        layout = QtWidgets.QVBoxLayout()

        # horizontally expanding spacer
        horizontally_expanding_spacer = QtWidgets.QLabel('')
        horizontally_expanding_spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        # file path controls
        path_layout = QtWidgets.QHBoxLayout()
        # label
        path_label = QtWidgets.QLabel('File Path')
        path_layout.addWidget(path_label)
        # browse path button
        self.browse_path_button = QtWidgets.QPushButton('Browse')
        self.browse_path_button.clicked.connect(self._browse_path_clicked)
        path_layout.addWidget(self.browse_path_button)
        # lineedit showing the file path
        self.path_lineedit = QtWidgets.QLineEdit()
        self.path_lineedit.setMinimumWidth(150)
        path_layout.addWidget(self.path_lineedit)
        # file type dropdown
        self.file_type_dropdown = QtWidgets.QComboBox()
        for f in self.filetypes:
            self.file_type_dropdown.addItem(f)
        path_layout.addWidget(self.file_type_dropdown)
        # load file button
        self.load_file_button = QtWidgets.QPushButton('Load')
        self.load_file_button.clicked.connect(self._load_file_clicked)
        path_layout.addWidget(self.load_file_button)
        # save file button
        self.save_file_button = QtWidgets.QPushButton('Save')
        self._disable_button(self.save_file_button)
        self.save_file_button.clicked.connect(self._save_file_clicked)
        path_layout.addWidget(self.save_file_button)

        layout.addLayout(path_layout)

        # data set controls
        dataset_layout = QtWidgets.QHBoxLayout()
        # label
        dataset_label = QtWidgets.QLabel('Data Set')
        dataset_layout.addWidget(dataset_label)
        # text box for the user to enter the name of the desired data set
        self.dataset_lineedit = QtWidgets.QLineEdit()
        self.dataset_lineedit.setMinimumWidth(150)
        dataset_layout.addWidget(self.dataset_lineedit)
        # pop data set button
        self.pop_dataset_button = QtWidgets.QPushButton('Pop')
        self.pop_dataset_button.clicked.connect(self._pop_dataset_clicked)
        dataset_layout.addWidget(self.pop_dataset_button)
        # push data set button
        self.push_dataset_button = QtWidgets.QPushButton('Push')
        self._disable_button(self.push_dataset_button)
        self.push_dataset_button.clicked.connect(self._push_dataset_clicked)
        dataset_layout.addWidget(self.push_dataset_button)

        layout.addLayout(dataset_layout)

        # list of data dictionary keys
        layout.addWidget(QtWidgets.QLabel('Keys'))
        self.key_list_widget = QtWidgets.QListWidget()
        self.key_list_widget.currentItemChanged.connect(self._key_selection_changed)
        layout.addWidget(self.key_list_widget)

        # key control buttons
        key_controls_layout = QtWidgets.QHBoxLayout()
        # button to update key text
        self.update_key_button = QtWidgets.QPushButton('Update')
        self._disable_button(self.update_key_button)
        self.update_key_button.clicked.connect(self._update_key_clicked)
        key_controls_layout.addWidget(self.update_key_button)
        # button to delete a key
        self.del_key_button = QtWidgets.QPushButton('Delete')
        self._disable_button(self.del_key_button)
        self.del_key_button.clicked.connect(self._del_key_clicked)
        key_controls_layout.addWidget(self.del_key_button)
        # button to add a key
        self.add_key_button = QtWidgets.QPushButton('Add')
        self._disable_button(self.add_key_button)
        self.add_key_button.clicked.connect(self._add_key_clicked)
        key_controls_layout.addWidget(self.add_key_button)
        # line edit for adding a new key
        self.add_key_lineedit = QtWidgets.QLineEdit()
        self.add_key_lineedit.setMinimumWidth(150)
        self.add_key_lineedit.setText('new key')
        key_controls_layout.addWidget(self.add_key_lineedit)

        layout.addLayout(key_controls_layout)

        layout.addWidget(QtWidgets.QLabel('Value'))

        self.value_textedit = QtWidgets.QTextEdit('')
        self.value_textedit.setEnabled(False)
        layout.addWidget(self.value_textedit)

        layout.addStretch()
        self.setLayout(layout)

        # data set
        self.data = None

    def _stop(self):
        self.backend.stop()

    def _disable_button(self, button):
        """Disable the button to prevent the user from pressing it.

        Args:
            button: QPushButton to disable.
        """

        # disabled button colors
        col_bg = QtGui.QColor(
            self.palette().color(QtGui.QPalette.ColorRole.AlternateBase)
        ).name()
        col_txt = QtGui.QColor(QtCore.Qt.GlobalColor.gray).name()

        # set the button disabled colors
        button.setStyleSheet(
            f'QPushButton {{background-color: {col_bg}; color: {col_txt};}}'
        )

        # disable the button
        button.setEnabled(False)

    def _enable_button(self, button):
        """Re-enable the button.

        Args:
            button: QPushButton to enable.
        """

        # default button colors
        col_bg = QtGui.QColor(
            self.palette().color(QtGui.QPalette.ColorRole.Button)
        ).name()
        col_txt = QtGui.QColor(
            self.palette().color(QtGui.QPalette.ColorRole.ButtonText)
        ).name()

        # set the default button colors
        button.setStyleSheet(
            f'QPushButton {{background-color: {col_bg}; color: {col_txt};}}'
        )
        # re-enable the button
        button.setEnabled(True)

    def _disable_all(self):
        """Disable all relevant GUI elements while the internal widget state isn't
        stable."""
        self._disable_button(self.save_file_button)
        self._disable_button(self.load_file_button)
        self._disable_button(self.push_dataset_button)
        self._disable_button(self.pop_dataset_button)
        self._disable_button(self.update_key_button)
        self._disable_button(self.add_key_button)
        self._disable_button(self.del_key_button)
        self.key_list_widget.setEnabled(False)
        self.value_textedit.setEnabled(False)

    def _enable_all(self):
        """Enable all relevant GUI elements once the internal widget state is stable."""
        self._enable_button(self.save_file_button)
        self._enable_button(self.load_file_button)
        self._enable_button(self.push_dataset_button)
        self._enable_button(self.pop_dataset_button)
        self._enable_button(self.update_key_button)
        self._enable_button(self.add_key_button)
        self._enable_button(self.del_key_button)
        self.key_list_widget.setEnabled(True)
        self.value_textedit.setEnabled(True)

    def _update_keys(self, keys):
        """Update the keys list view with the provided keys.

        Args:
            keys: The keys to update the list view with.

        """
        self.key_list_widget.clear()
        if keys is not None:
            for i in keys:
                self.key_list_widget.addItem(i)

    def _enable_all_and_update_keys(self, keys):
        """Enable all GUI elements and update the keys list view."""
        self._enable_all()
        self._update_keys(keys)

    def _browse_path_clicked(self):
        """Let the user pick a file path to save/load the data to/from."""

        # data set name
        dataset = self.dataset_lineedit.text()

        # make a file browser dialog to get the desired file location from the user
        path_dialog = QtWidgets.QFileDialog(self)
        path_dialog.setOption(QtWidgets.QFileDialog.Option.DontConfirmOverwrite)
        path_dialog.setLabelText(QtWidgets.QFileDialog.DialogLabel.Accept, 'Accept')
        path_dialog.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)
        path_dialog.setNameFilter(';;'.join(self.browse_filetype_filters))
        path_dialog.setViewMode(QtWidgets.QFileDialog.ViewMode.Detail)
        path_dialog.setDirectory(str(self.file_dialog_dir / f'{dataset}'))
        if path_dialog.exec():
            path = path_dialog.selectedFiles()[0]
            selected_filter = path_dialog.selectedNameFilter()
        else:
            # the user cancelled
            return

        # determine the selected file type
        selected_file_type = selected_filter.split(' ')[0]
        extensions = self.filetypes[selected_file_type][0]
        # add an extension if the user didn't provide it already
        if not any(ext in path for ext in extensions):
            path += extensions[0]

        self.path_lineedit.setText(path)
        self.file_type_dropdown.setCurrentText(selected_file_type)

    def _push_dataset_clicked(self):
        """Push data to the dataserver."""
        self._disable_all()
        self.backend.push(
            dataset=self.dataset_lineedit.text(), callback=self._enable_all
        )

    def _pop_dataset_clicked(self):
        """Pop data from the dataserver."""
        self._disable_all()
        self.backend.pop(
            dataset=self.dataset_lineedit.text(),
            timeout=self.timeout,
            callback=self._enable_all_and_update_keys,
        )

    def _save_file_clicked(self):
        """Save data to a file."""
        self._disable_all()
        self.backend.save(
            filename=self.path_lineedit.text(),
            save_fun=self.filetypes[self.file_type_dropdown.currentText()][1],
            callback=self._enable_all,
        )

    def _load_file_clicked(self):
        """Load data from a file."""
        self._disable_all()
        self.backend.load(
            filename=self.path_lineedit.text(),
            load_fun=self.filetypes[self.file_type_dropdown.currentText()][2],
            callback=self._enable_all_and_update_keys,
        )

    def _key_selection_changed(self):
        """Called when the key list selection is changed."""
        selected_item = self.key_list_widget.currentItem()
        if selected_item is None:
            self.value_textedit.setText('')
            self.value_textedit.setEnabled(False)
            return

        # retrieve the value from the backend
        val = self.backend.get_key(selected_item.text())
        if isinstance(val, str):
            # if the value is a string, display it in the value_textedit
            self.value_textedit.setText(val)
            self.value_textedit.setEnabled(True)
        else:
            self.value_textedit.setText('Not a string')
            self.value_textedit.setEnabled(False)

    def _update_key_clicked(self):
        """Called when the user presses the update key button."""
        selected_item = self.key_list_widget.currentItem()
        if selected_item is None:
            return
        selected_item_text = selected_item.text()

        # retrieve the value from the backend
        val = self.backend.get_key(selected_item_text)
        if isinstance(val, str):
            # if it's a string, set its new value
            self.backend.set_key(selected_item_text, self.value_textedit.toPlainText())
        else:
            raise RuntimeError(
                f'Cannot update key [{selected_item_text}] because it is not a string.'
            )

    def _add_key_clicked(self):
        """Called when the user presses the add key button."""
        self.backend.set_key(
            self.add_key_lineedit.text(), '', callback=self._update_keys
        )

    def _del_key_clicked(self):
        """Called when the user presses the delete key button."""
        selected_item = self.key_list_widget.currentItem()
        if selected_item is None:
            return

        self.backend.del_key(selected_item.text(), callback=self._update_keys)
