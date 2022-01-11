#!/usr/bin/env python
"""
This is an example script that demonstrates most of the basic functionality of nspyre.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging
from pathlib import Path

from nspyre import InstrumentGateway
from nspyre import nspyre_app
from nspyre import nspyre_init_logger
from nspyre import ParamsWidget
from nspyre import SplitterOrientation
from nspyre import SplitterWidget
from odmr import ODMR
from odmr import ODMRPlotWidget
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

        # create an instance of the ODMR class that implements the experimental logic
        self.odmr = ODMR(sg, daq)

        self.setWindowTitle('ODMR')

        # stacked layout of spinboxes that allow the user to enter experimental parameters
        self.params_widget = ParamsWidget(
            {
                'start_freq': {
                    'suffix': 'Hz',
                    'siPrefix': True,
                    'bounds': (100e3, 10e9),
                    'dec': True,
                },
                'stop_freq': {
                    'suffix': 'Hz',
                    'siPrefix': True,
                    'bounds': (100e3, 10e9),
                    'dec': True,
                },
                'num_points': {'int': True, 'bounds': (1, None), 'dec': True},
            }
        )

        # Qt button widget that takes an ODMR scan when clicked
        run_button = QPushButton('Sweep')
        run_button.clicked.connect(
            lambda: self.odmr.sweep(
                self.params_widget.start_freq,
                self.params_widget.stop_freq,
                self.params_widget.num_points,
            )
        )

        # data plotter
        self.ODMR_plot_widget = ODMRPlotWidget(
            title='ODMR Scan',
            xlabel='Frequency (s)',
            ylabel='PL (counts)',
            font=QFont('Arial', 18),
        )

        # Qt layout that arranges the params and button vertically
        params_layout = QVBoxLayout()
        params_layout.addWidget(self.params_widget)
        params_layout.addWidget(run_button)
        # widget containing the params and run button
        params_container = QWidget()
        params_container.setLayout(params_layout)

        # splitter that displays the params interface on the left and data viewer on the right
        self.splitter = SplitterWidget(
            main_w=params_container,
            side_w=self.ODMR_plot_widget,
            orientation=SplitterOrientation.vertical_right_button,
        )
        self.splitter.setSizes([1, 400])
        self.splitter.setHandleWidth(10)

        # Qt dummy layout that contains the splitter
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)


if __name__ == '__main__':
    # log to the console as well as a file inside the logs folder
    nspyre_init_logger(
        log_level=logging.INFO,
        log_path=HERE / 'logs',
        log_path_level=logging.DEBUG,
        prefix='odmr-gui',
        file_size=10_000_000,
    )

    # create Qt application and apply nspyre visual settings
    app = nspyre_app()

    # connect to the instrument server
    with InstrumentGateway() as isg:
        # create the GUI
        ODMR_widget = ODMRWidget(isg.sg, isg.daq)
        ODMR_widget.show()
        # run the GUI event loop
        app.exec()
