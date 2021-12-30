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

from nspyre import InstrumentGateway
from nspyre import nspyre_app
from nspyre import nspyre_init_logger
from nspyre import ParamsWidget
from odmr import ODMR
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget


class ODMRWidget(QWidget):
    """Qt widget subclass that generates an interface for running ODMR scans.
    It contains a set of boxes for the user to enter the experimental parameters,
    and a button to start the scan.
    """

    def __init__(self, sg, daq, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('ODMR Scan')

        # create an instance of the ODMR class implements the logic of the experiment
        self.odmr = ODMR(sg, daq)

        # Qt layout that arranges the params and button vertically
        layout = QVBoxLayout()

        # we just want a generic spyrelet UI, so tell nspyre the parameters needed
        # to create the Qt widgets as a dictionary
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


if __name__ == '__main__':
    # init logging
    nspyre_init_logger(logging.INFO)

    # create Qt application and apply nspyre visual settings
    app = nspyre_app(sys.argv)  # TODO name

    # connect to the instrument server
    with InstrumentGateway() as isg:
        # create the GUI
        ODMR_widget = ODMRWidget(isg.sg, isg.daq)
        ODMR_widget.show()
        # run the GUI event loop
        app.exec()
