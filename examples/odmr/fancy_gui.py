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
import nspyre
from nspyre import MainWidget
from nspyre import nspyre_app
from nspyre import nspyre_init_logger

HERE = Path(__file__).parent

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
main_widget = MainWidget(
    {
        'Save_File': {
            'module': nspyre,
            'class': 'SaveWidget',
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
