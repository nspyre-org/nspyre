"""
Example GUI elements for an ODMR application.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from functools import partial
from importlib import reload

import numpy as np
import spin_measurements
from nspyre import DataSink
from nspyre import LinePlotWidget
from nspyre import ParamsWidget
from nspyre import ProcessRunner
from nspyre import SaveWidget
from pyqtgraph.Qt import QtWidgets


class ODMRWidget(QtWidgets.QWidget):
    """Qt widget subclass that generates an interface for running ODMR scans.
    It contains a set of boxes for the user to enter the experimental parameters,
    and a button to start the scan.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle('ODMR')

        # stacked layout of spinboxes that allow the user to enter experimental parameters
        self.params_widget = ParamsWidget(
            {
                'start_freq': {
                    'display_text': 'Start Frequency',
                    'value': 3e9,
                    'suffix': 'Hz',
                    'siPrefix': True,
                    'bounds': (100e3, 10e9),
                    'dec': True,
                },
                'stop_freq': {
                    'display_text': 'Stop Frequency',
                    'value': 4e9,
                    'suffix': 'Hz',
                    'siPrefix': True,
                    'bounds': (100e3, 10e9),
                    'dec': True,
                },
                'num_points': {
                    'display_text': 'Number of points',
                    'value': 100,
                    'int': True,
                    'bounds': (1, None),
                    'dec': True,
                },
            }
        )

        # Qt button widget that takes an ODMR scan when clicked
        sweep_button = QtWidgets.QPushButton('Sweep')
        # the process running the sweep function
        self.sweep_proc = ProcessRunner()
        # start run sweep_clicked on button press
        sweep_button.clicked.connect(self.sweep_clicked)

        # Qt button widget that takes an ODMR scan when clicked
        stop_button = QtWidgets.QPushButton('Stop')
        # start run sweep_clicked on button press
        stop_button.clicked.connect(self.stop)
        # stop the process if the widget is destroyed
        self.destroyed.connect(partial(self.stop))

        # Qt layout that arranges the params and button vertically
        params_layout = QtWidgets.QVBoxLayout()
        params_layout.addWidget(self.params_widget)
        params_layout.addStretch()
        params_layout.addWidget(stop_button)
        params_layout.addWidget(sweep_button)

        self.setLayout(params_layout)

    def sweep_clicked(self):
        """Runs when the 'sweep' button is pressed."""

        # reload the spin measurements module at runtime in case any changes were made to the code
        reload(spin_measurements)

        # create an instance of the ODMR class that implements the experimental logic.
        spin_meas = spin_measurements.SpinMeasurements()

        # run the sweep function in a new thread.
        self.sweep_proc.run(
            spin_meas.odmr_sweep,
            self.params_widget.start_freq,
            self.params_widget.stop_freq,
            self.params_widget.num_points,
        )

    def stop(self):
        """Stop the sweep process."""
        self.sweep_proc.kill()


def save_ODMR(filename, data):
    np.savez(filename, freqs=data['freqs'], counts=data['counts'])


class ODMRSaveWidget(SaveWidget):
    def __init__(self):
        super().__init__(additional_filetypes={'ODMR': save_ODMR})


class ODMRPlotWidget(LinePlotWidget):
    def __init__(self):
        super().__init__(
            title='ODMR @ B = 15mT', xlabel='Frequency (GHz)', ylabel='PL (counts)'
        )

    def setup(self):
        self.new_plot('ODMR')
        self.plot_widget.setYRange(-100, 5100)
        self.sink = DataSink('ODMR')
        self.sink.start()

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
