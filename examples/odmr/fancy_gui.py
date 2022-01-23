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

import gui_elements
import nspyre
from nspyre import nspyre_app
from nspyre import nspyre_init_logger
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
        self.setWindowTitle('nspyre')
        self.resize(1200, 700)

        # list of available widgets
        self.widgets = {
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
        """Runs when the 'load' button is pressed. Loads the relevant widget and adds it to the dock area."""
        widget_name = self.list_widget.currentItem().text()
        widget_module = self.widgets[widget_name]['module']
        widget_class_name = self.widgets[widget_name]['class']
        widget_args = self.widgets[widget_name]['args']
        widget_kwargs = self.widgets[widget_name]['kwargs']

        # reload the module at runtime in case any changes were made to the code
        widget_module = reload(widget_module)
        widget_class = getattr(widget_module, widget_class_name)
        # create an instance of the widget class
        widget = widget_class(*widget_args, **widget_kwargs)
        # add the widget to the GUI
        self.dock_widget(widget, widget_name)

    def dock_widget(self, widget, title, closable=True, fontSize='16px'):
        """Create a new dock for the given widget and add it to the dock area."""
        dock = Dock(
            title,
            size=(500, 200),
            autoOrientation=False,
            closable=closable,
            fontSize=fontSize,
        )
        dock.setOrientation(o='vertical', force=True)
        dock.addWidget(widget)
        self.docks.append(dock)
        self.dock_area.addDock(dock, 'right')


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
    main_widget = MainWidget()
    main_widget.show()
    # Run the GUI event loop.
    app.exec()
