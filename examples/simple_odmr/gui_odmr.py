#!/usr/bin/env python
"""
This is an example script that demonstrates the basic functionality of nspyre.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
from pathlib import Path

from nspyre import DataSink
from nspyre import LinePlotWidget
from nspyre import nspyre_app
from nspyre import nspyre_init_logger
from nspyre import ParamsWidget
from nspyre import ProcessRunner
from nspyre import SplitterOrientation
from nspyre import SplitterWidget
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget
from spin_measurements import SpinMeasurements

HERE = Path(__file__).parent

logger = logging.getLogger(__name__)


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
                    'value': 10,
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

        # Data plotter widget
        self.plot_widget = ODMRPlotWidget(
            title='ODMR Scan',
            xlabel='Frequency (GHz)',
            ylabel='PL (counts)',
            font=QFont('Arial', 14),
        )

        # Qt layout that arranges the params and button vertically
        params_layout = QVBoxLayout()
        params_layout.addWidget(self.params_widget)
        params_layout.addWidget(sweep_button)
        # Dummy widget containing the params and run button
        params_container = QWidget()
        params_container.setLayout(params_layout)

        # Splitter that displays the params interface on the left and data viewer on the right
        self.splitter = SplitterWidget(
            main_w=params_container,
            side_w=self.plot_widget,
            orientation=SplitterOrientation.vertical_right_button,
        )
        self.splitter.setSizes([1, 400])

        # Qt dummy layout that contains the splitter
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

    def sweep_clicked(self):
        """Runs when the 'sweep' button is pressed."""

        # Create an instance of the ODMR class that implements the experimental logic.
        spin_meas = SpinMeasurements()

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
        prefix='odmr',
        file_size=10_000_000,
    )

    # Create Qt application and apply nspyre visual settings.
    app = nspyre_app()

    # Create the GUI.
    ODMR_widget = ODMRWidget()
    ODMR_widget.show()
    # Run the GUI event loop.
    app.exec()
