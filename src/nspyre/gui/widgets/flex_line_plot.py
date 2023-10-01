import logging
import time
from typing import Callable
from typing import Optional

import numpy as np
from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

from ...data.sink import DataSink
from ..threadsafe import QThreadSafeObject
from .layout import tree_layout
from .line_plot import LinePlotWidget

_logger = logging.getLogger(__name__)


class _FlexLinePlotSeriesSettings:
    """Contain the settings for a single plot."""

    def __init__(
        self, series: str, scan_i: str, scan_j: str, processing: str, hidden: bool
    ):
        self.series: str = series
        self.scan_i: str = scan_i
        self.scan_j: str = scan_j
        self.processing: str = processing
        self.hidden = hidden


class _FlexLinePlotSettings(QThreadSafeObject):
    """Container class to hold the plot settings for a _FlexLinePlotWidget."""

    def __init__(self):
        self.series_settings = {}
        # DataSink for pulling plot data from the data server
        self.sink = None
        # protect access to the sink
        self.sink_mutex = QtCore.QMutex()
        # flag indicating that the plots should be updated
        self.force_update = False
        super().__init__()

    def get_settings(self, name: str, callback=None):
        with QtCore.QMutexLocker(self.mutex):
            settings = self.series_settings[name]
            if callback is not None:
                self.run_main(callback, name, settings, blocking=True)

    def add_plot(
        self,
        name: str,
        series: str,
        scan_i: str,
        scan_j: str,
        processing: str,
        hidden: bool,
        callback: Optional[Callable] = None,
    ):
        with QtCore.QMutexLocker(self.mutex):
            if name in self.series_settings:
                _logger.info(
                    f'A plot with the name [{name}] already exists. Ignoring add_plot '
                    'request.'
                )
                return
            self.series_settings[name] = _FlexLinePlotSeriesSettings(
                series=series,
                scan_i=scan_i,
                scan_j=scan_j,
                processing=processing,
                hidden=hidden,
            )
            self.force_update = True
            if callback is not None:
                self.run_main(callback, name, blocking=True)

    def remove_plot(self, name, callback=None):
        with QtCore.QMutexLocker(self.mutex):
            if name not in self.series_settings:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring '
                    'remove_plot request.'
                )
                return

            if callback is not None:
                self.run_main(callback, name, blocking=True)

            del self.series_settings[name]

    def hide_plot(self, name, callback=None):
        with QtCore.QMutexLocker(self.mutex):
            if name not in self.series_settings:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring '
                    'hide_plot request.'
                )
                return
            if self.series_settings[name].hidden:
                _logger.info(
                    f'The plot [{name}] is already hidden. Ignoring hide_plot request.'
                )
                return
            self.series_settings[name].hidden = True
            if callback is not None:
                self.run_main(callback, name, blocking=True)

    def show_plot(self, name, callback=None):
        with QtCore.QMutexLocker(self.mutex):
            if name not in self.series_settings:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring show_plot '
                    'request.'
                )
                return
            if not self.series_settings[name].hidden:
                _logger.info(
                    f'The plot [{name}] is already shown. Ignoring show_plot request.'
                )
                return
            self.series_settings[name].hidden = False
            if callback is not None:
                self.run_main(callback, name, blocking=True)

    def update_settings(self, name, series, scan_i, scan_j, processing):
        with QtCore.QMutexLocker(self.mutex):
            if name not in self.series_settings:
                _logger.info(
                    f'A plot with the name [{name}] does not exist. Ignoring '
                    'update_settings request.'
                )
                return
            self.series_settings[name].series = series
            self.series_settings[name].scan_i = scan_i
            self.series_settings[name].scan_j = scan_j
            self.series_settings[name].processing = processing
            self.force_update = True


class FlexLinePlotWidget(QtWidgets.QWidget):
    """Qt widget for flexible plotting of 1D user data.
    It connects to an arbitrary data set stored in the
    :py:class:`~nspyre.data.server.DataServer`, collects and processes the data, and
    offers a variety of user-controlled plotting options.

    The user should push a dictionary containing the following key/value pairs
    to the corresponding :py:class:`~nspyre.data.source.DataSource`
    object sourcing data to the :py:class:`~nspyre.data.server.DataServer`:

    - key: :code:`title`, value: Plot title string
    - key: :code:`xlabel`, value: X label string
    - key: :code:`ylabel`, value: Y label string
    - key: :code:`datasets`, value: Dictionary where keys are a data series \
        name, and values are data as a list of 2D numpy arrays of shape (2, n). \
        The two rows represent the x and y axes, respectively, of the plot, and \
        the n columns each represent a data point.

    You may use np.NaN values in the data arrays to represent invalid entries,
    which won't contribute to the data averaging. An example is given below:

    .. code-block:: python

        from nspyre import DataSource, StreamingList

        with DataSource('my_dataset') as ds:
            channel_1_data = StreamingList([np.array([[1, 2, 3], [12, 12.5, 12.25]]), \
np.array([[4, 5, 6], [12.6, 13, 11.2]])])
            channel_2_data = StreamingList([np.array([[1, 2, 3], [3, 3.3, 3.1]]), \
np.array([[4, 5, 6], [3.4, 3.6, 3.5]])])
            my_plot_data = {
                'title': 'MyVoltagePlot',
                'xlabel': 'Time (s)',
                'ylabel': 'Amplitude (V)',
                'datasets': {
                    'channel_1': channel_1_data
                    'channel_2': channel_2_data
                }
            }
            ds.push(my_plot_data)

    """

    def __init__(
        self, timeout: float = 1, data_processing_func: Optional[Callable] = None
    ):
        """
        Args:
            timeout: Timeout for :py:meth:`~nspyre.data.sink.DataSink.pop`.
            data_processing_func: Function to do any post-processing of the data
                popped by the :py:class:`~nspyre.data.sink.DataSink`. Takes one
                argument, which is the :py:class:`~nspyre.data.sink.DataSink`.
        """
        super().__init__()

        self.line_plot = _FlexLinePlotWidget(
            timeout=timeout, data_processing_func=data_processing_func
        )
        """Underlying LinePlotWidget."""

        # data source lineedit
        self.datasource_lineedit = QtWidgets.QLineEdit()

        # data source connect button
        connect_button = QtWidgets.QPushButton('Connect')
        connect_button.clicked.connect(self._update_source_clicked)

        # plot settings label
        plot_settings_label = QtWidgets.QLabel('Plot Settings')
        plot_settings_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)

        # plot name lineedit
        self.plot_name_lineedit = QtWidgets.QLineEdit('avg')

        # data series lineedit
        self.plot_series_lineedit = QtWidgets.QLineEdit('series1')

        # scan indices lineedits
        self.add_plot_scan_i_textbox = QtWidgets.QLineEdit()
        self.add_plot_scan_j_textbox = QtWidgets.QLineEdit()

        # avg/append label
        plot_processing_label = QtWidgets.QLabel('Processing')
        plot_processing_label.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed
            )
        )

        # avg/append dropdown
        self.plot_processing_dropdown = QtWidgets.QComboBox()
        self.plot_processing_dropdown.addItem('Average')  # index 0
        self.plot_processing_dropdown.addItem('Append')  # index 1
        # default to average
        self.plot_processing_dropdown.setCurrentIndex(0)

        # show button
        show_button = QtWidgets.QPushButton('Show')
        show_button.clicked.connect(self._show_plot_clicked)

        # hide button
        hide_button = QtWidgets.QPushButton('Hide')
        hide_button.clicked.connect(self._hide_plot_clicked)

        # update button
        update_plot_button = QtWidgets.QPushButton('Update')
        update_plot_button.clicked.connect(self._update_plot_clicked)

        # add button
        add_plot_button = QtWidgets.QPushButton('Add')
        add_plot_button.clicked.connect(self._add_plot_clicked)

        # del button
        remove_button = QtWidgets.QPushButton('Remove')
        remove_button.clicked.connect(self._remove_plot_clicked)

        # plots label
        plots_label = QtWidgets.QLabel('Plots')
        plots_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)

        # list of plots
        self.plots_list_widget = QtWidgets.QListWidget()
        self.plots_list_widget.currentItemChanged.connect(self._plot_selection_changed)

        # spacer
        fixed_spacer = QtWidgets.QLabel('')
        fixed_spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed
        )

        # spacer
        expanding_spacer = QtWidgets.QLabel('')
        expanding_spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        # layout
        settings_layout_config = {
            'type': QtWidgets.QVBoxLayout,
            'data_source': {
                'type': QtWidgets.QHBoxLayout,
                'label': QtWidgets.QLabel('Data Set'),
                'edit': self.datasource_lineedit,
                'button': connect_button,
            },
            'config': {
                'type': QtWidgets.QHBoxLayout,
                'plot': {
                    'type': QtWidgets.QVBoxLayout,
                    'label': plot_settings_label,
                    'settings': {
                        'type': QtWidgets.QVBoxLayout,
                        'name': {
                            'type': QtWidgets.QHBoxLayout,
                            'label': QtWidgets.QLabel('Plot Name'),
                            'edit': self.plot_name_lineedit,
                        },
                        'series': {
                            'type': QtWidgets.QHBoxLayout,
                            'label': QtWidgets.QLabel('Data Series'),
                            'edit': self.plot_series_lineedit,
                        },
                        'index': {
                            'type': QtWidgets.QHBoxLayout,
                            'l1': QtWidgets.QLabel('Scan'),
                            'i': self.add_plot_scan_i_textbox,
                            'l2': QtWidgets.QLabel(' to '),
                            'j': self.add_plot_scan_j_textbox,
                        },
                        'processing': {
                            'type': QtWidgets.QHBoxLayout,
                            'label': plot_processing_label,
                            'dropdown': self.plot_processing_dropdown,
                        },
                        'spacer': expanding_spacer,
                    },
                },
                'settings_buttons': {
                    'type': QtWidgets.QVBoxLayout,
                    'spacer_t': fixed_spacer,
                    'update': update_plot_button,
                    'add': add_plot_button,
                    'remove': remove_button,
                    'spacer_b': expanding_spacer,
                },
                'plots': {
                    'type': QtWidgets.QVBoxLayout,
                    'label': plots_label,
                    'list': self.plots_list_widget,
                },
                'list_buttons': {
                    'type': QtWidgets.QVBoxLayout,
                    'spacer_t': fixed_spacer,
                    'show': show_button,
                    'hide': hide_button,
                    'spacer_b': expanding_spacer,
                },
            },
        }
        self.layout_tree = tree_layout(settings_layout_config)
        # make the plots list (index=2) take up all extra space (stretch=1)
        self.layout_tree.config.layout.setStretch(2, 1)

        # splitter
        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
        splitter.addWidget(self.line_plot)
        layout_container = QtWidgets.QWidget()
        layout_container.setLayout(self.layout_tree.layout)
        splitter.addWidget(layout_container)

        # main layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(splitter)

        self.setLayout(layout)

    def _plot_selection_changed(self):
        """Called when the selected plot changes."""
        # selected QListWidgetItem
        selected_item = self.plots_list_widget.currentItem()
        if selected_item is None:
            return
        # get the selected plot name
        name = selected_item.text()
        self.line_plot.plot_settings.run_safe(
            self.line_plot.plot_settings.get_settings,
            name,
            callback=self._plot_selection_changed_callback,
        )

    def _plot_selection_changed_callback(
        self, name: str, settings: _FlexLinePlotSeriesSettings
    ):
        """Called after the selection is changed to update the plot settings GUI
        elements."""
        self.plot_name_lineedit.setText(name)
        self.plot_series_lineedit.setText(settings.series)
        self.add_plot_scan_i_textbox.setText(settings.scan_i)
        self.add_plot_scan_j_textbox.setText(settings.scan_j)
        self.plot_processing_dropdown.setCurrentText(settings.processing)

    def _get_plot_settings(self):
        """Retrieve the user-entered plot settings from the GUI and check them for
        errors."""
        scan_i = self.add_plot_scan_i_textbox.text()
        try:
            if scan_i != '':
                int(scan_i)
        except ValueError as err:
            raise ValueError(
                f'Scan start [{scan_i}] must be either an integer or empty.'
            ) from err
        scan_j = self.add_plot_scan_j_textbox.text()
        try:
            if scan_j != '':
                int(scan_j)
        except ValueError as err:
            raise ValueError(
                f'Scan end [{scan_j}] must be either an integer or empty.'
            ) from err
        name = self.plot_name_lineedit.text()
        series = self.plot_series_lineedit.text()
        processing = self.plot_processing_dropdown.currentText()

        return name, series, scan_i, scan_j, processing

    def _update_plot_clicked(self):
        """Called when the user clicks the update button."""
        name, series, scan_i, scan_j, processing = self._get_plot_settings()
        # set the plot settings
        self.line_plot.plot_settings.run_safe(
            self.line_plot.plot_settings.update_settings,
            name,
            series,
            scan_i,
            scan_j,
            processing,
        )

    def _add_plot_clicked(self):
        """Called when the user clicks the add button."""
        name, series, scan_i, scan_j, processing = self._get_plot_settings()
        self.add_plot(name, series, scan_i, scan_j, processing)

    def add_plot(
        self, name: str, series: str, scan_i: str, scan_j: str, processing: str
    ):
        """Add a new subplot. Thread safe.

        Args:
            name: Name for the new plot.
            series: The data series name pushed by the \
                :py:class:`~nspyre.data.source.DataSource`, e.g. \
                :code:`channel_1` for the example given in \
                :py:class:`~nspyre.gui.widgets.flex_line_plot.FlexLinePlotWidget`
            scan_i: String value of the scan to start plotting from.
            scan_j: String value of the scan to stop plotting at. \
                Use Python list indexing notation, e.g.:

                - :code:`scan_i = '-1'`, :code:`scan_j = ''` for the last element
                - :code:`scan_i = '0'`, :code:`scan_j = '1'` for the first element
                - :code:`scan_i = '-3'`, :code:`scan_j = ''` for the last 3 elements.

            processing: 'Average' to average the x and y values of scans i
                through j, 'Append' to concatenate them.
        """
        self.line_plot.plot_settings.run_safe(
            self.line_plot.plot_settings.add_plot,
            name,
            series,
            scan_i,
            scan_j,
            processing,
            False,
            callback=self._add_plot_callback,
        )

    def _add_plot_callback(self, name: str):
        """Called in main thread after a plot is added."""
        self.plots_list_widget.addItem(name)
        self.line_plot.add_plot(name)

    def _find_plot_item(self, name):
        """Return the index of the list widget plot item with the given name."""
        list_widget_index = None
        for i in range(self.plots_list_widget.count()):
            if self.plots_list_widget.item(i).text() == name:
                list_widget_index = i
                break
        if list_widget_index is None:
            raise RuntimeError(
                f'Internal error: plot [{name}] not found in list widget.'
            )

        return list_widget_index

    def _remove_plot_clicked(self):
        """Called when the user clicks the remove button."""
        # array of selected QListWidgetItems
        selected_items = self.plots_list_widget.selectedItems()
        for i in selected_items:
            name = i.text()
            self.remove_plot(name)

    def remove_plot(self, name: str):
        """Remove a subplot. Thread safe.

        Args:
            name: Name of the subplot.
        """
        # remove the plot settings
        self.line_plot.plot_settings.run_safe(
            self.line_plot.plot_settings.remove_plot,
            name,
            callback=self._remove_plot_callback,
        )

    def _remove_plot_callback(self, name: str):
        """Called in main thread after a plot is removed."""
        # remove the plot name from the list of plots
        self.plots_list_widget.takeItem(self._find_plot_item(name))
        # remove the plot from the pyqtgraph plotwidget
        self.line_plot.remove_plot(name)

    def _hide_plot_clicked(self):
        """Called when the user clicks the hide button."""
        # array of selected QListWidgetItems
        selected_items = self.plots_list_widget.selectedItems()
        for i in selected_items:
            name = i.text()
            self.hide_plot(name)

    def hide_plot(self, name: str):
        """Hide a subplot. Thread safe.

        Args:
            name: Name of the subplot.
        """
        # update the settings
        self.line_plot.plot_settings.run_safe(
            self.line_plot.plot_settings.hide_plot,
            name,
            callback=self._hide_plot_callback,
        )

    def _hide_plot_callback(self, name: str):
        """Called in main thread after a plot is hidden."""
        # hide the plot in the pyqtgraph plotting widget
        self.line_plot.hide_plot(name)
        # change the list widget item color scheme
        idx = self._find_plot_item(name)
        self.plots_list_widget.item(idx).setForeground(QtCore.Qt.GlobalColor.gray)
        self.plots_list_widget.item(idx).setBackground(
            self.palette().color(QtGui.QPalette.ColorRole.Mid)
        )

    def _show_plot_clicked(self):
        """Called when the user clicks the show button."""
        # array of selected QListWidgetItems
        selected_items = self.plots_list_widget.selectedItems()
        for i in selected_items:
            name = i.text()
            self.show_plot(name)

    def show_plot(self, name: str):
        """Show a previously hidden subplot. Thread safe.

        Args:
            name: Name of the subplot.
        """
        # update the settings
        self.line_plot.plot_settings.run_safe(
            self.line_plot.plot_settings.show_plot,
            name,
            callback=self._show_plot_callback,
        )

    def _show_plot_callback(self, name: str):
        """Called after a plot is shown."""
        # show the plot in the pyqtgraph plotting widget
        self.line_plot.show_plot(name)
        # return list widget item to normal color scheme
        idx = self._find_plot_item(name)
        normal_text_color = self.palette().color(QtGui.QPalette.ColorRole.Text)
        normal_bg_color = self.palette().color(QtGui.QPalette.ColorRole.Base)
        self.plots_list_widget.item(idx).setForeground(normal_text_color)
        self.plots_list_widget.item(idx).setBackground(normal_bg_color)

    def _update_source_clicked(self):
        """Called when the user clicks the connect button."""
        self.line_plot.new_source(self.datasource_lineedit.text())


class _FlexLinePlotWidget(LinePlotWidget):
    """See FlexLinePlotWidget."""

    def __init__(self, timeout: float, data_processing_func: Optional[Callable]):
        """
        Args:
            timeout: see :py:class:`FlexLinePlotWidget`.
            data_processing_func: see :py:class:`FlexLinePlotWidget`.
        """
        self.timeout = timeout
        self.data_processing_func = data_processing_func
        self.plot_settings = _FlexLinePlotSettings()
        self.plot_settings.start()
        super().__init__()

    def _stop(self):
        """Stop the updating and plot data management threads."""
        self.plot_settings.stop()
        super()._stop()

    def new_source(self, data_set_name: str):
        """Connect to a new data set on the data server.

        Args:
            data_set_name: Name of the new data set.
        """
        # run on the plot_settings thread since we'll need to acquire mutexes
        self.plot_settings.run_safe(self._new_source, data_set_name)

    def _new_source(self, data_set_name: str):
        # connect to a new data set
        with QtCore.QMutexLocker(self.plot_settings.sink_mutex):
            self.clear_plots()
            try:
                # connect to the new data source
                self.plot_settings.sink = DataSink(data_set_name)
                self.plot_settings.sink.start()

                # try to get the plot title and x/y labels
                self.plot_settings.sink.pop(timeout=self.timeout)

                # set title
                try:
                    title = self.plot_settings.sink.title
                except AttributeError:
                    _logger.info(
                        f'Data source [{data_set_name}] has no "title" '
                        'attribute. Not setting the plot title...'
                    )
                    title = None

                # set xlabel
                try:
                    xlabel = self.plot_settings.sink.xlabel
                except AttributeError:
                    _logger.info(
                        f'Data source [{data_set_name}] has no "xlabel" '
                        'attribute. Not setting the plot x-axis label...'
                    )
                    xlabel = None

                # set ylabel
                try:
                    ylabel = self.plot_settings.sink.ylabel
                except AttributeError:
                    _logger.info(
                        f'Data source [{data_set_name}] has no "ylabel" '
                        'attribute. Not setting the plot y-axis label...'
                    )
                    ylabel = None

                # try to access datasets
                try:
                    dsets = self.plot_settings.sink.datasets
                except AttributeError as err:
                    raise RuntimeError(
                        f'Data source [{data_set_name}] has no "datasets" attribute - '
                        'exiting...'
                    ) from err
                else:
                    if not isinstance(dsets, dict):
                        raise RuntimeError(
                            f'Data source [{data_set_name}] "datasets" attribute is '
                            'not a dictionary - exiting...'
                        )

                # set the new title/labels in the main thread
                self.plot_settings.run_main(
                    self._new_source_callback, title, xlabel, ylabel, blocking=True
                )

                # add the existing plots
                with QtCore.QMutexLocker(self.plot_settings.mutex):
                    for plot_name in self.plot_settings.series_settings:
                        self.add_plot(plot_name)
                        if self.plot_settings.series_settings[plot_name].hidden:
                            self.hide_plot(plot_name)

                # force plot the data since we used the first pop() to extract the
                # plot info
                self.plot_settings.force_update = True
            except (TimeoutError, RuntimeError) as err:
                self.teardown()
                raise RuntimeError(
                    f'Could not connect to new data source [{data_set_name}]'
                ) from err

    def _new_source_callback(self, title, xlabel, ylabel):
        """Callback for when a new data source connects."""
        if title is not None:
            self.set_title(title)
        if xlabel is not None:
            self.xaxis.setLabel(text=xlabel)
        if ylabel is not None:
            self.yaxis.setLabel(text=ylabel)

    def teardown(self):
        """Clean up."""
        # run on the plot_settings thread since we'll need to acquire mutexes
        self.plot_settings.run_safe(self._close_source)

    def _close_source(self):
        """Disconnect from the data source."""
        with QtCore.QMutexLocker(self.plot_settings.sink_mutex):
            if self.plot_settings.sink is not None:
                self.plot_settings.sink.stop()
                self.plot_settings.sink = None

    def update(self):
        """Update the plot if there is new data available."""
        with QtCore.QMutexLocker(self.plot_settings.sink_mutex):
            if self.plot_settings.sink is None:
                # rate limit how often update() runs if there is no sink connected
                time.sleep(0.1)
                return

            if self.plot_settings.force_update:
                self.plot_settings.force_update = False
            else:
                try:
                    # wait for new data to be available from the sink
                    self.plot_settings.sink.pop(timeout=self.timeout)
                except TimeoutError:
                    return

            if self.data_processing_func is not None:
                self.data_processing_func(self.plot_settings.sink)

            with QtCore.QMutexLocker(self.plot_settings.mutex):
                for plot_name in self.plot_settings.series_settings:
                    settings = self.plot_settings.series_settings[plot_name]
                    series = settings.series
                    scan_i = settings.scan_i
                    scan_j = settings.scan_j
                    processing = settings.processing

                    # pick out the particular data series
                    try:
                        data = self.plot_settings.sink.datasets[series]
                    except KeyError:
                        _logger.error(f'Data series [{series}] does not exist.')
                        continue

                    if not isinstance(data, list):
                        raise ValueError(
                            f'Data series [{series}] must be a list of numpy arrays, '
                            f'but has type [{type(data)}].'
                        )

                    if len(data) == 0:
                        continue
                    else:
                        # check for numpy array
                        if not isinstance(data[0], np.ndarray):
                            raise ValueError(
                                f'Data series [{series}] must be a list of numpy '
                                'arrays, but the first list element has type '
                                f'[{type(data[0])}].'
                            )
                        # check numpy array shape
                        if data[0].shape[0] != 2 or len(data[0].shape) != 2:
                            raise ValueError(
                                f'Data series [{series}] first list element has '
                                f'shape {data.shape}, but should be (2, n).'
                            )

                        try:
                            if scan_i == '' and scan_j == '':
                                data_subset = data[:]
                            elif scan_j == '':
                                data_subset = data[int(scan_i) :]
                            elif scan_i == '':
                                data_subset = data[: int(scan_j)]
                            else:
                                data_subset = data[int(scan_i) : int(scan_j)]
                        except IndexError:
                            _logger.warning(
                                f'Data series [{series}] invalid scan indices '
                                f'[{scan_i}, {scan_j}].'
                            )
                            continue

                        if processing == 'Append':
                            # concatenate the numpy arrays
                            processed_data = np.concatenate(data_subset, axis=1)
                        elif processing == 'Average':
                            # create a single numpy array
                            stacked_data = np.stack(data_subset)
                            # mask the NaN entries
                            masked_data = np.ma.array(
                                stacked_data, mask=np.isnan(stacked_data)
                            )
                            # average the numpy arrays
                            processed_data = np.ma.average(masked_data, axis=0)
                        else:
                            raise ValueError(
                                f'Processing has unsupported value [{processing}].'
                            )

                    # update the plot
                    self.set_data(plot_name, processed_data[0], processed_data[1])
