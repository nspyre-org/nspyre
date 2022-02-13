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

import gui_elements
from nspyre import MainWidget
from nspyre import nspyre_init_logger
from nspyre import NspyreApp

HERE = Path(__file__).parent

# if using the nspyre ProcessRunner, the main code must be guarded with if __name__ == '__main__':
# see https://docs.python.org/2/library/multiprocessing.html#windows
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
    app = NspyreApp()

    # Create the GUI.
    main_widget = MainWidget(
        {
            'SaveODMR': {
                'module': gui_elements,
                'class': 'ODMRSaveWidget',
                'args': (),
                'kwargs': {},
            },
            'ODMR': {
                'module': gui_elements,
                'class': 'ODMRWidget',
                'args': (),
                'kwargs': {},
            },
            'ODMR_plot': {
                'module': gui_elements,
                'class': 'ODMRPlotWidget',
                'args': (),
                'kwargs': {},
            },
            'ODMR_scroll_plot': {
                'module': gui_elements,
                'class': 'ScrollingODMRPlotWidget',
                'args': (),
                'kwargs': {},
            },
        }
    )
    main_widget.show()
    # Run the GUI event loop.
    app.exec()
