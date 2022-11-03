"""
A plotting widget that connects to an nspyre data server, collects and processes the data, and offers a variety of user-controlled plotting options.

Copyright (c) 2022, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
import time
from threading import Lock

import numpy as np
from nspyre import DataSink
from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtWidgets

from .line_plot_widget import LinePlotWidget

logger = logging.getLogger(__name__)


class FlexLinePlotWidget(QtWidgets.QWidget):
    """QWidget that allows the user to connect to an arbitrary nspyre DataSource and plot its data.

    The DataSource may contain the following attributes:
    title: plot title string
    xlabel: x label string
    ylabel: y label string
    datasets: dictionary where keys are a data series name, and values are data
    as a list of 2D numpy array like
    [np.array([[x0, x1, ...], [y0, y1, ...]]), np.array([[x10, x11, ...], [y10, y11, ...]]), ...]

    """

    def __init__(self):
        """Init FlexLinePlotWidget."""
        super().__init__()

        layout = QtWidgets.QVBoxLayout()

        # lineplot widget
        self.flex_line_plot = _FlexLinePlotWidget()

        # lineedit and button for selecting the data source
        datasource_layout = QtWidgets.QHBoxLayout()
        self.datasource_lineedit = QtWidgets.QLineEdit()
        self.update_button = QtWidgets.QPushButton('Connect')
        self.update_button.clicked.connect(self._update_source)
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
        plot_name_layout.addWidget(QtWidgets.QLabel('Name'))
        self.plot_name_lineedit = QtWidgets.QLineEdit('avg')
        plot_name_layout.addWidget(self.plot_name_lineedit)
        plot_add_layout.addLayout(plot_name_layout)

        # plot series
        plot_data_series_layout = QtWidgets.QHBoxLayout()
        plot_data_series_layout.addWidget(QtWidgets.QLabel('Series'))
        self.plot_series_lineedit = QtWidgets.QLineEdit('mydata')
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
        self.show_button.clicked.connect(self._show_plot)
        plot_actions_layout.addWidget(self.show_button)
        # hide button
        self.hide_button = QtWidgets.QPushButton('Hide')
        self.hide_button.clicked.connect(self._hide_plot)
        plot_actions_layout.addWidget(self.hide_button)
        # update button
        self.add_plot_button = QtWidgets.QPushButton('Update')
        self.add_plot_button.clicked.connect(self._update_plot)
        plot_actions_layout.addWidget(self.add_plot_button)
        # add button
        self.add_plot_button = QtWidgets.QPushButton('Add')
        self.add_plot_button.clicked.connect(self._add_plot)
        plot_actions_layout.addWidget(self.add_plot_button)
        # del button
        self.remove_button = QtWidgets.QPushButton('Remove')
        self.remove_button.clicked.connect(self._remove_plot)
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
        splitter.addWidget(self.flex_line_plot)
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
        series = self.flex_line_plot.plot_settings[name]['series']
        scan_i = self.flex_line_plot.plot_settings[name]['scan_i']
        scan_j = self.flex_line_plot.plot_settings[name]['scan_j']
        processing = self.flex_line_plot.plot_settings[name]['processing']
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

    def _update_plot(self):
        """Called when the user clicks the update button."""
        name, series, scan_i, scan_j, processing = self._get_plot_settings()
        # set the plot settings
        self.flex_line_plot.new_plot_settings(name, series, scan_i, scan_j, processing)

    def _add_plot(self):
        """Called when the user clicks the add button."""
        name, series, scan_i, scan_j, processing = self._get_plot_settings()
        if name in self.flex_line_plot.plot_settings:
            raise ValueError(f'Plot [{name}] already exists.')
        # add the plot to the pyqtgraph plotwidget
        self.flex_line_plot.add_plot(name)
        # set the plot settings
        self.flex_line_plot.plot_settings[name] = {
            'series': series,
            'scan_i': scan_i,
            'scan_j': scan_j,
            'processing': processing,
        }
        # add the plot name to the list of plots
        self.plots_list_widget.addItem(name)

    def _remove_plot(self):
        """Called when the user clicks the remove button."""
        # array of selected QListWidgetItems
        selected_items = self.plots_list_widget.selectedItems()
        for i in selected_items:
            name = i.text()
            if name not in self.flex_line_plot.plot_settings:
                raise ValueError(f'Plot [{name}] does not exist.')
            # remove the plot name from the list of plots
            self.plots_list_widget.takeItem(self.plots_list_widget.row(i))
            # remove the plot settings
            self.flex_line_plot.plot_settings.pop(name)
            # remove the plot from the pyqtgraph plotwidget
            self.flex_line_plot.remove_plot(name)

    def _hide_plot(self):
        """Called when the user clicks the hide button."""
        # array of selected QListWidgetItems
        selected_items = self.plots_list_widget.selectedItems()
        for i in selected_items:
            name = i.text()
            self.flex_line_plot.hide(name)

    def _show_plot(self):
        """Called when the user clicks the show button."""
        # array of selected QListWidgetItems
        selected_items = self.plots_list_widget.selectedItems()
        for i in selected_items:
            name = i.text()
            self.flex_line_plot.show(name)

    def _update_source(self):
        """Called when the user clicks the connect button."""
        self.flex_line_plot.new_source(self.datasource_lineedit.text())


class _FlexLinePlotWidget(LinePlotWidget):
    """See FlexLinePlotWidget."""

    def __init__(self):
        super().__init__()
        self.sink = None
        # mutex for protecting access to the data sink
        self.mutex = Lock()
        self.plot_settings = {}

    def new_plot_settings(self, name, series, scan_i, scan_j, processing):
        with self.mutex:
            self.plot_settings[name] = {
                'series': series,
                'scan_i': scan_i,
                'scan_j': scan_j,
                'processing': processing,
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
                if self.sink.pop(timeout=timeout):
                    # set title
                    try:
                        title = self.sink.title
                    except AttributeError:
                        logger.info(
                            f'Data source [{data_source_name}] has no "title" attribute - skipping...'
                        )
                    else:
                        self.set_title(title)
                    # set xlabel
                    try:
                        xlabel = self.sink.xlabel
                    except AttributeError:
                        logger.info(
                            f'Data source [{data_source_name}] has no "xlabel" attribute - skipping...'
                        )
                    else:
                        self.xaxis.setLabel(text=xlabel)
                    # set ylabel
                    try:
                        ylabel = self.sink.ylabel
                    except AttributeError:
                        logger.info(
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
                            logger.error(
                                f'Data source [{data_source_name}] "datasets" attribute is not a dictionary - exiting...'
                            )
                            raise RuntimeError
                    # add the existing plots
                    for plot_name in self.plot_settings:
                        self.add_plot(plot_name)
                else:
                    # some other pop error occured
                    raise RuntimeError
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
        if self.sink is not None and self.sink.pop():
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
                            logger.error(
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
                                        data_subset = data[int(scan_i) : int(scan_j)]
                                except IndexError:
                                    logger.warning(
                                        f'Data series [{series}] invalid scan indices [{scan_i}, {scan_j}]'
                                    )
                                    continue

                                if processing == 'Append':
                                    # concatenate the numpy arrays
                                    processed_data = np.concatenate(data_subset, axis=1)
                                elif processing == 'Average':
                                    # average the numpy arrays
                                    processed_data = np.average(
                                        np.stack(data_subset), axis=0
                                    )
                                else:
                                    raise ValueError(
                                        f'processing has unsupported value [{processing}].'
                                    )
                        else:
                            raise ValueError(
                                f'Data series [{series}] must be a list of numpy arrays, but has type [{type(data)}].'
                            )

                        # update the plot
                        self.set_data(plot_name, processed_data[0], processed_data[1])
        else:
            time.sleep(0.1)
