#!/usr/bin/env python
"""
This is an example script that demonstrates the basic functionality of nspyre.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
from importlib import reload
from pathlib import Path

import spin_measurements
from nspyre import DataSink
from nspyre import LinePlotWidget
from nspyre import nspyre_app
from nspyre import nspyre_init_logger
from nspyre import ParamsWidget
from nspyre import ProcessRunner
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QListWidgetItem
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget
from pyqtgraph.dockarea import Dock
from pyqtgraph.dockarea import DockArea

HERE = Path(__file__).parent

logger = logging.getLogger(__name__)


class MainWidget(QWidget):
    """Qt widget that contains a list of widgets to run, and a pyqtgraph DockArea where they are displayed."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # window settings
        self.setWindowTitle('My Experiment')
        self.resize(1200, 700)

        # list of available widgets
        self.widgets = {
            'ODMR': {'cls': ODMRWidget, 'args': (), 'kwargs': {}},
            'ODMR_plot': {'cls': ODMRPlotWidget, 'args': (), 'kwargs': {}},
            'ODMR_scroll_plot': {
                'cls': ScrollingODMRPlotWidget,
                'args': (),
                'kwargs': {},
            },
        }

        # dock area to view the widgets
        self.dock_area = DockArea()
        self.docks = []

        # make a GUI element to show all the available widgets
        self.list_widget = QListWidget()
        for w in self.widgets:
            QListWidgetItem(w, self.list_widget)

        # Qt button that loads a widget from the widget list when clicked
        load_button = QPushButton('Load')
        # run the load widget method on button press
        load_button.clicked.connect(self.load_widget_clicked)

        # Qt layout that arranges the widget list and run button vertically
        widget_list_layout = QVBoxLayout()
        widget_list_layout.addWidget(self.list_widget)
        widget_list_layout.addWidget(load_button)
        # Dummy widget containing the list widget and run button
        widget_list_container = QWidget()
        widget_list_container.setLayout(widget_list_layout)

        # add the widget list to the dock area
        self.dock_widget(widget_list_container, 'Widgets', closable=False)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.dock_area)
        self.setLayout(main_layout)

    def load_widget_clicked(self):
        """Runs when the 'run' button is pressed. Loads the relevant widget and adds it to the dock area."""
        widget_name = self.list_widget.currentItem().text()
        widget_cls = self.widgets[widget_name]['cls']
        widget_args = self.widgets[widget_name]['args']
        widget_kwargs = self.widgets[widget_name]['kwargs']
        widget = widget_cls(*widget_args, **widget_kwargs)
        self.dock_widget(widget, widget_name)

    def dock_widget(self, widget, title, closable=True, fontSize='14px'):
        dock = Dock(
            title,
            size=(500, 200),
            autoOrientation=False,
            closable=closable,
            fontSize=fontSize,
        )
        dock.setOrientation(o='vertical', force=True)
        self.dock_area.addDock(dock, 'right')
        dock.addWidget(widget)
        self.docks.append(dock)


class ODMRWidget(QWidget):
    """Qt widget subclass that generates an interface for running ODMR scans.
    It contains a set of boxes for the user to enter the experimental parameters,
    and a button to start the scan.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('ODMR')

        # Stacked layout of spinboxes that allow the user to enter experimental parameters
        self.params_widget = ParamsWidget(
            {
                'start_freq': {
                    'value': 2e9,
                    'suffix': 'Hz',
                    'siPrefix': True,
                    'bounds': (100e3, 10e9),
                    'dec': True,
                },
                'stop_freq': {
                    'value': 3e9,
                    'suffix': 'Hz',
                    'siPrefix': True,
                    'bounds': (100e3, 10e9),
                    'dec': True,
                },
                'num_points': {
                    'value': 100,
                    'int': True,
                    'bounds': (1, None),
                    'dec': True,
                },
            }
        )

        # Qt button widget that takes an ODMR scan when clicked
        sweep_button = QPushButton('Sweep')
        # The process running the sweep function
        self.sweep_proc = ProcessRunner()
        # Start run sweep_clicked on button press
        sweep_button.clicked.connect(self.sweep_clicked)

        # Qt layout that arranges the params and button vertically
        params_layout = QVBoxLayout()
        params_layout.addWidget(self.params_widget)
        params_layout.addWidget(sweep_button)

        self.setLayout(params_layout)

    def sweep_clicked(self):
        """Runs when the 'sweep' button is pressed."""

        # reload the spin measurements module at runtime in case any changes were made to the code
        reload(spin_measurements)

        # Create an instance of the ODMR class that implements the experimental logic.
        spin_meas = spin_measurements.SpinMeasurements()

        # Run the sweep function in a new thread.
        self.sweep_proc.run(
            spin_meas.odmr_sweep,
            self.params_widget.start_freq,
            self.params_widget.stop_freq,
            self.params_widget.num_points,
        )

    def closeEvent(self, event):
        event.accept()
        self.plot_widget.stop()


class ODMRPlotWidget(LinePlotWidget):
    def setup(self):
        self.new_plot('ODMR')
        self.plot_widget.setYRange(-100, 5100)
        self.sink = DataSink('ODMR')

    def teardown(self):
        self.sink.stop()

    def update(self):
        if self.sink.pop():
            # update the plot
            self.set_data(
                'ODMR',
                self.sink.freqs[0 : self.sink.idx + 1] / 1e9,
                self.sink.counts[0 : self.sink.idx + 1],
            )


class ScrollingODMRPlotWidget(ODMRPlotWidget):
    def update(self):
        if self.sink.pop():
            # scrolling behavior
            # index of last point to plot
            end_idx = self.sink.idx
            # max number of points to display simultaneously
            npts = 10
            if end_idx > npts:
                # index of first point to plot
                start_idx = end_idx - npts
            else:
                start_idx = 0
            # update the plot
            self.set_data(
                'ODMR',
                self.sink.freqs[start_idx : end_idx + 1] / 1e9,
                self.sink.counts[start_idx : end_idx + 1],
            )


if __name__ == '__main__':
    # Log to the console as well as a file inside the logs folder.
    nspyre_init_logger(
        log_level=logging.INFO,
        log_path=HERE / 'logs',
        log_path_level=logging.DEBUG,
        prefix='fancy_odmr',
        file_size=10_000_000,
    )

    # Create Qt application and apply nspyre visual settings.
    app = nspyre_app()

    # Create the GUI.
    ODMR_widget = MainWidget()
    ODMR_widget.show()
    # Run the GUI event loop.
    app.exec()
