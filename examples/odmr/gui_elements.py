"""
Example GUI elements for an ODMR application.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from importlib import reload

import spin_measurements
from nspyre import DataSink
from nspyre import LinePlotWidget
from nspyre import ParamsWidget
from nspyre import ProcessRunner
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget


class ODMRWidget(QWidget):
    """Qt widget subclass that generates an interface for running ODMR scans.
    It contains a set of boxes for the user to enter the experimental parameters,
    and a button to start the scan.
    """

    def __init__(self):
        super().__init__()

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
            end_idx = self.sink.idx + 1
            # max number of points to display simultaneously
            npts = 20
            if end_idx > npts:
                # index of first point to plot
                start_idx = end_idx - npts
            else:
                start_idx = 0
            # update the plot
            self.set_data(
                'ODMR',
                self.sink.freqs[start_idx:end_idx] / 1e9,
                self.sink.counts[start_idx:end_idx],
            )
