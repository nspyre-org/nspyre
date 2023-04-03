import logging
import time
from threading import Lock

import numpy as np
from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

from ...data.sink import DataSink
from .line_plot import LinePlotWidget

_logger = logging.getLogger(__name__)


class FlexLinePlotWidget(QtWidgets.QWidget):
    """Qt widget for flexible plotting of user data. 
    It connects to an arbitrary data set stored in the :py:class:`~nspyre.data.server.DataServer`,
    collects and processes the data, and offers a variety of user-controlled 
    plotting options.

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
            channel_1_data = StreamingList([np.array([[1, 2, 3], [12, 12.5, 12.25]]), np.array([[4, 5, 6], [12.6, 13, 11.2]])])
            channel_2_data = StreamingList([np.array([[1, 2, 3], [3, 3.3, 3.1]]), np.array([[4, 5, 6], [3.4, 3.6, 3.5]])])
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

    def __init__(self):
        super().__init__()

        layout = QtWidgets.QVBoxLayout()

        self.line_plot = _FlexLinePlotWidget()
        """Underlying LinePlotWidget."""

        # lineedit and button for selecting the data source
        datasource_layout = QtWidgets.QHBoxLayout()
        self.datasource_lineedit = QtWidgets.QLineEdit()
        self.update_button = QtWidgets.QPushButton('Connect')
        self.update_button.clicked.connect(self._update_source_clicked)
        datasource_layout.addWidget(QtWidgets.QLabel('Data Set'))
        datasource_layout.addWidget(self.datasource_lineedit)
        datasource_layout.addWidget(self.update_button)

        # contains plot settings
        plot_settings_layout = QtWidgets.QHBoxLayout()

        # add new subplot layout
        plot_add_layout = QtWidgets.QVBoxLayout()
        plot_settings_label = QtWidgets.QLabel('Plot Settings')
        plot_settings_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        plot_add_layout.addWidget(plot_settings_label)

        # plot name
        plot_name_layout = QtWidgets.QHBoxLayout()
        plot_name_layout.addWidget(QtWidgets.QLabel('Plot Name'))
        self.plot_name_lineedit = QtWidgets.QLineEdit('avg')
        plot_name_layout.addWidget(self.plot_name_lineedit)
        plot_add_layout.addLayout(plot_name_layout)

        # plot series
        plot_data_series_layout = QtWidgets.QHBoxLayout()
        plot_data_series_layout.addWidget(QtWidgets.QLabel('Data Series'))
        self.plot_series_lineedit = QtWidgets.QLineEdit('series1')
        plot_data_series_layout.addWidget(self.plot_series_lineedit)
        plot_add_layout.addLayout(plot_data_series_layout)

        # scan indices layout
        scan_indices_layout = QtWidgets.QHBoxLayout()
        scan_indices_layout.addWidget(QtWidgets.QLabel('Scan'))
        self.add_plot_scan_i_textbox = QtWidgets.QLineEdit()
        scan_indices_layout.addWidget(self.add_plot_scan_i_textbox)
        scan_indices_layout.addWidget(QtWidgets.QLabel(' to '))
        self.add_plot_scan_j_textbox = QtWidgets.QLineEdit()
        scan_indices_layout.addWidget(self.add_plot_scan_j_textbox)

        plot_add_layout.addLayout(scan_indices_layout)

        # average / append
        plot_processing_layout = QtWidgets.QHBoxLayout()
        plot_processing_label = QtWidgets.QLabel('Processing')
        plot_processing_label.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed
            )
        )
        plot_processing_layout.addWidget(plot_processing_label)
        self.plot_processing_dropdown = QtWidgets.QComboBox()
        self.plot_processing_dropdown.addItem('Average')  # index 0
        self.plot_processing_dropdown.addItem('Append')  # index 1
        # default to average
        self.plot_processing_dropdown.setCurrentIndex(0)
        plot_processing_layout.addWidget(self.plot_processing_dropdown)
        plot_add_layout.addLayout(plot_processing_layout)

        plot_add_layout.addStretch()
        plot_settings_layout.addLayout(plot_add_layout)
        # set to minimum size
        plot_add_layout.setSizeConstraint(
            QtWidgets.QLayout.SizeConstraint.SetMinimumSize
        )

        # subplot show/hide/add/del buttons
        plot_actions_layout = QtWidgets.QVBoxLayout()
        # show button
        self.show_button = QtWidgets.QPushButton('Show')
        self.show_button.clicked.connect(self._show_plot_clicked)
        plot_actions_layout.addWidget(self.show_button)
        # hide button
        self.hide_button = QtWidgets.QPushButton('Hide')
        self.hide_button.clicked.connect(self._hide_plot_clicked)
        plot_actions_layout.addWidget(self.hide_button)
        # update button
        self.add_plot_button = QtWidgets.QPushButton('Update')
        self.add_plot_button.clicked.connect(self._update_plot_clicked)
        plot_actions_layout.addWidget(self.add_plot_button)
        # add button
        self.add_plot_button = QtWidgets.QPushButton('Add')
        self.add_plot_button.clicked.connect(self._add_plot_clicked)
        plot_actions_layout.addWidget(self.add_plot_button)
        # del button
        self.remove_button = QtWidgets.QPushButton('Remove')
        self.remove_button.clicked.connect(self._remove_plot_clicked)
        plot_actions_layout.addWidget(self.remove_button)
        plot_actions_layout.addStretch()
        plot_settings_layout.addLayout(plot_actions_layout)

        # list of plots
        self.plots_list_widget = QtWidgets.QListWidget()
        self.plots_list_widget.currentItemChanged.connect(self._plot_selection_changed)
        plot_settings_layout.addWidget(self.plots_list_widget)

        # layout for containing the data source selection layout and the plot settings layout
        settings_layout = QtWidgets.QVBoxLayout()
        settings_layout.addLayout(datasource_layout)
        settings_layout.addLayout(plot_settings_layout)
        # widget for containing the settings layout
        settings_widget = QtWidgets.QWidget()
        settings_widget.setLayout(settings_layout)

        # splitter
        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
        splitter.addWidget(self.line_plot)
        splitter.addWidget(settings_widget)

        # main layout
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
        # retrieve all of the associated info for this plot
        series = self.line_plot.plot_settings[name]['series']
        scan_i = self.line_plot.plot_settings[name]['scan_i']
        scan_j = self.line_plot.plot_settings[name]['scan_j']
        processing = self.line_plot.plot_settings[name]['processing']
        # update the plot settings GUI elements
        self.plot_name_lineedit.setText(name)
        self.add_plot_scan_i_textbox.setText(scan_i)
        self.add_plot_scan_j_textbox.setText(scan_j)
        self.plot_series_lineedit.setText(series)
        self.plot_processing_dropdown.setCurrentText(processing)

    def _get_plot_settings(self):
        """Retrieve the user-entered plot settings from the GUI and check them for errors."""
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
        self.line_plot.update_plot_settings(
            name, series, scan_i, scan_j, processing
        )
        self.line_plot.force_update = True

    def _add_plot_clicked(self):
        """Called when the user clicks the add button."""
        name, series, scan_i, scan_j, processing = self._get_plot_settings()
        self.add_plot(name, series, scan_i, scan_j, processing)
        self.line_plot.force_update = True

    def add_plot(
        self, name: str, series: str, scan_i: str, scan_j: str, processing: str
    ):
        """Add a new subplot.

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
        if name in self.line_plot.plot_settings:
            raise ValueError(f'Plot [{name}] already exists.')
        with self.line_plot.mutex:
            # add the plot to the pyqtgraph plotwidget
            self.line_plot.add_plot(name)
            # set the plot settings
            self.line_plot.plot_settings[name] = {
                'series': series,
                'scan_i': scan_i,
                'scan_j': scan_j,
                'processing': processing,
                'hidden': False,
            }
            # add the plot name to the list of plots
            self.plots_list_widget.addItem(name)

    def _find_plot_item(self, name):
        """Return the index of the list widget plot item with the given name."""
        if name not in self.line_plot.plot_settings:
            raise ValueError(f'Plot [{name}] does not exist.')

        # search for the list widget item whose text is the same as name
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
        """Remove a subplot.

        Args:
            name: Name of the subplot.
        """
        with self.line_plot.mutex:
            # remove the plot name from the list of plots
            self.plots_list_widget.takeItem(self._find_plot_item(name))
            # remove the plot settings
            self.line_plot.plot_settings.pop(name)
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
        """Hide a subplot.

        Args:
            name: Name of the subplot.
        """
        with self.line_plot.mutex:
            self.line_plot.plot_settings[name]['hidden'] = True
            self.line_plot.hide(name)
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
        """Show a previously hidden subplot.

        Args:
            name: Name of the subplot.
        """
        with self.line_plot.mutex:
            self.line_plot.plot_settings[name]['hidden'] = False
            self.line_plot.show(name)
            # return list widget item to normal color scheme
            # text
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

    def __init__(self):
        super().__init__()
        self.sink = None
        # mutex for protecting access to the data sink and plot settings
        self.mutex = Lock()
        self.plot_settings = {}
        # flag indicating that this is the first pop from the sink
        self.force_update = False

    def update_plot_settings(self, name, series, scan_i, scan_j, processing):
        with self.mutex:
            if name not in self.plot_settings:
                raise ValueError(f'Plot [{name}] does not exist.')
            hidden = self.plot_settings[name]['hidden']
            self.plot_settings[name] = {
                'series': series,
                'scan_i': scan_i,
                'scan_j': scan_j,
                'processing': processing,
                'hidden': hidden,
            }

    def new_source(self, data_source_name, timeout=1):
        # connect to a new data set
        with self.mutex:
            self.teardown()
            self.data_source_name = data_source_name

            # clear previous plots
            self.plot_widget.getPlotItem().clear()
            self.plots = {}

            # try to get the plot title and x/y labels
            try:
                self.sink = DataSink(self.data_source_name)
                self.sink.__enter__()
                self.sink.pop(timeout=timeout)
                # set title
                try:
                    title = self.sink.title
                except AttributeError:
                    _logger.info(
                        f'Data source [{data_source_name}] has no "title" attribute - skipping...'
                    )
                else:
                    self.set_title(title)
                # set xlabel
                try:
                    xlabel = self.sink.xlabel
                except AttributeError:
                    _logger.info(
                        f'Data source [{data_source_name}] has no "xlabel" attribute - skipping...'
                    )
                else:
                    self.xaxis.setLabel(text=xlabel)
                # set ylabel
                try:
                    ylabel = self.sink.ylabel
                except AttributeError:
                    _logger.info(
                        f'Data source [{data_source_name}] has no "ylabel" attribute - skipping...'
                    )
                else:
                    self.yaxis.setLabel(text=ylabel)
                try:
                    dsets = self.sink.datasets
                except AttributeError as err:
                    raise RuntimeError(
                        f'Data source [{data_source_name}] has no "datasets" attribute - exiting...'
                    ) from err
                else:
                    if not isinstance(dsets, dict):
                        _logger.error(
                            f'Data source [{data_source_name}] "datasets" attribute is not a dictionary - exiting...'
                        )
                        raise RuntimeError
                # add the existing plots
                for plot_name in self.plot_settings:
                    self.add_plot(plot_name)
                    if self.plot_settings[plot_name]['hidden']:
                        self.hide(plot_name)
                # flag indicating that this is the first pop from the sink
                self.force_update = True
            except (TimeoutError, RuntimeError) as err:
                self.teardown()
                raise RuntimeError(
                    f'Could not connect to new data source [{data_source_name}]'
                ) from err

    def teardown(self):
        if self.sink is not None:
            self.sink.__exit__(None, None, None)
            self.sink = None

    def update(self):
        # update the plot data
        # plot immediately if this is the first time, otherwise wait for new
        # data to be available from the sink with pop()
        try:
            if self.sink is not None:
                if not self.force_update:
                    self.sink.pop(timeout=0.1)
                with self.mutex:
                    # check again to be sure
                    if self.sink is not None:
                        for plot_name in self.plot_settings:
                            series = self.plot_settings[plot_name]['series']
                            scan_i = self.plot_settings[plot_name]['scan_i']
                            scan_j = self.plot_settings[plot_name]['scan_j']
                            processing = self.plot_settings[plot_name]['processing']

                            # pick out the particulary data series
                            try:
                                data = self.sink.datasets[series]
                            except KeyError:
                                _logger.error(
                                    f'Data series [{series}] does not exist in data set [{self.data_source_name}]'
                                )
                                continue

                            if isinstance(data, list):
                                if len(data) == 0:
                                    continue
                                else:
                                    # check for numpy array
                                    if not isinstance(data[0], np.ndarray):
                                        raise ValueError(
                                            f'Data series [{series}] must be a list of numpy arrays, but the first list element has type [{type(data[0])}].'
                                        )
                                    # check numpy array shape
                                    if data[0].shape[0] != 2 or len(data[0].shape) != 2:
                                        raise ValueError(
                                            f'Data series [{series}] first list element has shape {data.shape}, but should be (2, n).'
                                        )

                                    try:
                                        if scan_i == '' and scan_j == '':
                                            data_subset = data[:]
                                        elif scan_j == '':
                                            data_subset = data[int(scan_i) :]
                                        elif scan_i == '':
                                            data_subset = data[: int(scan_j)]
                                        else:
                                            data_subset = data[
                                                int(scan_i) : int(scan_j)
                                            ]
                                    except IndexError:
                                        _logger.warning(
                                            f'Data series [{series}] invalid scan indices [{scan_i}, {scan_j}]'
                                        )
                                        continue

                                    if processing == 'Append':
                                        # concatenate the numpy arrays
                                        processed_data = np.concatenate(
                                            data_subset, axis=1
                                        )
                                    elif processing == 'Average':
                                        # create a single numpy array
                                        stacked_data = np.stack(data_subset)
                                        # mask the NaN entries
                                        masked_data = np.ma.array(stacked_data, mask=np.isnan(stacked_data))
                                        # average the numpy arrays
                                        processed_data = np.ma.average(masked_data, axis=0)
                                    else:
                                        raise ValueError(
                                            f'Processing has unsupported value [{processing}].'
                                        )
                            else:
                                raise ValueError(
                                    f'Data series [{series}] must be a list of numpy arrays, but has type [{type(data)}].'
                                )

                            # update the plot
                            self.set_data(
                                plot_name, processed_data[0], processed_data[1]
                            )
                self.force_update = False
            else:
                time.sleep(0.1)
        except TimeoutError:
            pass
