#!/usr/bin/env python
"""
This is an example script that demonstrates most of the basic functionality of nspyre.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
import sys
from pathlib import Path

import numpy as np
from nspyre import InstrumentGateway
from nspyre import LinePlotWidget
from nspyre import nspyre_app
from nspyre import nspyre_init_logger
from nspyre import ParamsWidget
from odmr import ODMR
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

HERE = Path(__file__).parent


class ODMRWidget(QWidget):
    """Qt widget subclass that generates an interface for running ODMR scans.
    It contains a set of boxes for the user to enter the experimental parameters,
    and a button to start the scan.
    """

    def __init__(self, sg, daq, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('ODMR')

        # create an instance of the ODMR class that implements the experimental logic
        self.odmr = ODMR(sg, daq)

        # Qt layout that arranges the params and button vertically
        layout = QVBoxLayout()

        # stacked layout of spinboxes that allow the user to enter experimental parameters
        self.params_widget = ParamsWidget(
            {
                'start': {
                    'suffix': 'Hz',
                    'siPrefix': True,
                    'bounds': (100e3, 10e9),
                    'dec': True,
                },
                'stop': {
                    'suffix': 'Hz',
                    'siPrefix': True,
                    'bounds': (100e3, 10e9),
                    'dec': True,
                },
                'num_points': {'int': True, 'bounds': (1, None), 'dec': True},
            }
        )
        layout.addWidget(self.params_widget)

        # Qt button widget that takes an ODMR scan when clicked
        run_button = QPushButton('Sweep')
        run_button.clicked.connect(
            lambda: self.odmr.sweep(
                self.params_widget.start,
                self.params_widget.stop,
                self.params_widget.num_points,
            )
        )
        layout.addWidget(run_button)

        self.setLayout(layout)


class ODMRPlotWidget(LinePlotWidget):
    def setup(self):
        self.new_plot('ODMR+')
        self.new_plot('ODMR-')
        self.plot_widget.setYRange(-3, 3)

    def update(self):
        f = np.linspace(0, 1000, num=1000)
        c1 = np.random.normal(size=len(f))
        c2 = np.random.normal(size=len(f))
        self.set_data('ODMR+', f, c1)
        self.set_data('ODMR-', f, c2)


if __name__ == '__main__':
    # log to the console as well as a file inside the logs folder
    nspyre_init_logger(
        logging.DEBUG,
        log_path=HERE / 'logs',
        log_path_level=logging.DEBUG,
        prefix='odmr-gui',
        file_size=10_000_000,
    )

    # create Qt application and apply nspyre visual settings
    app = nspyre_app(sys.argv)

    # connect to the instrument server
    with InstrumentGateway() as isg:
        # create the GUI
        # ODMR_widget = ODMRWidget(isg.sg, isg.daq)
        ODMR_widget = ODMRPlotWidget(
            title='ODMR Scan',
            xlabel='Frequency (s)',
            ylabel='PL (counts)',
            font=QFont('Arial', 18),
        )
        ODMR_widget.show()
        # run the GUI event loop
        app.exec()
