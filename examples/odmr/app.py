#!/usr/bin/env python
"""
This is an example script that demonstrates the basic functionality of nspyre.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import argparse
import logging
from pathlib import Path

import gui_elements
import nspyre.gui.widgets.line_plot_widget
import nspyre.gui.widgets.snake
from nspyre import MainWidget
from nspyre import MainWidgetItem
from nspyre import nspyre_init_logger
from nspyre import NSpyreApp

# in order for dynamic reloading of code to work, you must pass the specifc
# module containing your class to MainWidgetItem, since the python reload()
# function it does not recursively reload modules

HERE = Path(__file__).parent


def main():
    arg_parser = argparse.ArgumentParser(description='Run the Biosensing2 GUI.')
    arg_parser.add_argument(
        '-v',
        '--verbosity',
        default='info',
        help='Log level: info, debug, warning, or error',
    )

    cmd_line_args = arg_parser.parse_args()
    match cmd_line_args.verbosity:
        case 'debug':
            log_level = logging.DEBUG
        case 'info':
            log_level = logging.INFO
        case 'warning':
            log_level = logging.WARNING
        case 'error':
            log_level = logging.ERROR
        case _:
            raise ValueError(f'log level [{cmd_line_args.verbosity}] not supported')

    # Log to the console as well as a file inside the logs folder.
    nspyre_init_logger(
        log_level=log_level,
        log_path=HERE / 'logs',
        log_path_level=logging.DEBUG,
        prefix='fancy_odmr',
        file_size=10_000_000,
    )

    # Create Qt application and apply nspyre visual settings.
    app = NSpyreApp()

    # Create the GUI.
    main_widget = MainWidget(
        {
            'Save ODMR': MainWidgetItem(gui_elements, 'ODMRSaveWidget', stretch=(1, 1)),
            'ODMR': MainWidgetItem(gui_elements, 'ODMRWidget', stretch=(1, 1)),
            'Plots': {
                'ODMR Plot': MainWidgetItem(
                    gui_elements, 'ODMRPlotWidget', stretch=(100, 100)
                ),
                'ODMR Scroll Plot': MainWidgetItem(
                    gui_elements, 'ScrollingODMRPlotWidget', stretch=(100, 100)
                ),
                'FlexSinkLinePlot': MainWidgetItem(
                    nspyre.gui.widgets.line_plot_widget,
                    'FlexSinkLinePlotWidget',
                    stretch=(100, 100),
                ),
            },
            'Snake': MainWidgetItem(nspyre.gui.widgets.snake, 'sssss'),
        }
    )
    main_widget.show()
    # Run the GUI event loop.
    app.exec()


# if using the nspyre ProcessRunner, the main code must be guarded with if __name__ == '__main__':
# see https://docs.python.org/2/library/multiprocessing.html#windows
if __name__ == '__main__':
    main()
