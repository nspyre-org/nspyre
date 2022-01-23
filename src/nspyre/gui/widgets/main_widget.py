"""
This widget creates an interface that allows the user to easily launch Qt widgets. The widgets are placed in a pyqtgraph dock area.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from importlib import reload

from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QListWidgetItem
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget
from pyqtgraph.dockarea import Dock
from pyqtgraph.dockarea import DockArea

from .sssss import sssss


class MainWidget(QWidget):
    """Qt widget that contains a list of widgets to run, and a pyqtgraph DockArea where they are displayed."""

    def __init__(self, widgets, font_size='18px'):
        """
        Typical usage example:

            .. code-block:: python

                import my_module
                import nspyre
                from nspyre import nspyre_app
                from nspyre import MainWidget

                # Create Qt application and apply nspyre visual settings.
                app = nspyre_app()

                # Create the GUI.
                main_widget = MainWidget({
                    'Save_File': {
                        'module': nspyre,
                        'class': 'SaveWidget',
                        'args': (),
                        'kwargs': {},
                    },
                    'ODMR': {
                        'module': my_module,
                        'class': 'ODMRWidget',
                        'args': (),
                        'kwargs': {},
                    },
                })
                main_widget.show()
                # Run the GUI event loop.
                app.exec()

        Args:
            widgets: Dictionary - see example usage for the required form.
            font_size: Dock label font size as a string (e.g. '14px').
        """
        super().__init__()

        # window settings
        self.setWindowTitle('nspyre')
        self.resize(1200, 700)
        self.font_size = font_size

        # dict of available widgets
        self.widgets = widgets

        # dock area to view the widgets
        self.dock_area = DockArea()

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
        widget_list_dock = self.dock_widget(widget_list_container, name='Widgets')
        # set size relative to other docks
        widget_list_dock.setStretch(20, 1)

        # add the snake logo
        logo_widget = sssss()
        self.logo_dock = self.dock_widget(logo_widget, name='snake')
        self.logo_dock.hideTitleBar()
        self.logo_dock.setStretch(80, 1)

        main_layout = QVBoxLayout()
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
        dock = self.dock_widget(widget, name=widget_name, closable=True)
        dock.setStretch(80, 1)

    def dock_widget(self, widget, *args, **kwargs):
        """Create a new dock for the given widget and add it to the dock area."""
        # if the logo dock is there, remove it
        try:
            self.logo_dock.close()
        except AttributeError:
            pass

        if 'fontSize' not in kwargs:
            kwargs['fontSize'] = self.font_size
        if 'autoOrientation' not in kwargs:
            # https://github.com/pyqtgraph/pyqtgraph/issues/1762
            kwargs['autoOrientation'] = False
        # create the dock and add it to the dock area
        dock = Dock(*args, **kwargs)
        dock.setOrientation(o='vertical', force=True)
        dock.addWidget(widget)
        self.dock_area.addDock(dock, 'right')

        return dock
