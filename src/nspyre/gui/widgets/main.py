"""
Creates an interface that allows the user to easily launch Qt widgets. The
widgets are placed in a pyqtgraph :code:`DockArea`.
"""
from importlib import reload
from types import ModuleType

from pyqtgraph.dockarea import Dock
from pyqtgraph.dockarea import DockArea
from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

from .snake import sssss


class MainWidgetItem:
    """Represents an arbitrary QWidget that can be loaded from the MainWidget."""

    def __init__(
        self,
        module: ModuleType,
        cls: str,
        args: list = None,
        kwargs: dict = None,
        stretch: tuple = None,
    ):
        """
        Args:
            name: Display name for the widget.
            module: Python module that contains cls.
            cls: Python class name as a string (that descends from QWidget).
                An instance of this class will be created when the user tries
                to load the widget and it will be added to the :code:`DockArea`.
            args: Arguments to pass to the __init__ function of cls.
            kwargs: Keyword arguments to pass to the __init__ function of cls.
            stretch: The dock stretch factor as a tuple (stretch_x, stretch_y) \
                (see https://pyqtgraph.readthedocs.io/en/latest/api_reference/dockarea.html)
        """
        super().__init__()
        self.module = module
        self.cls = cls
        self.stretch = stretch
        if args is None:
            self.args = []
        else:
            self.args = args
        if kwargs is None:
            self.kwargs = {}
        else:
            self.kwargs = kwargs


class _MainWidgetItem(QtGui.QStandardItem):
    """A leaf node in the QTreeView of the MainWidget which contains the
    information for launching the widget."""

    def __init__(self, name: str, main_widget_item: MainWidgetItem):
        """
        Args:
            name: display name for the widget
            main_widget_item: instance of MainWidgetItem
        """
        super().__init__()
        self.name = name
        self.main_widget_item = main_widget_item
        self.setEditable(False)
        self.setText(name)


class _MainWidgetItemContainer(QtGui.QStandardItem):
    """A non-leaf node in the QTreeView of the MainWidget"""

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.setEditable(False)
        self.setText(name)


class MainWidget(QtWidgets.QWidget):
    """Qt widget for loading other QWidgets.
    It displays a hierarchy of widgets for the user to select and launch, and a
    pyqtgraph :code:`DockArea` where they are displayed. The widgets dictionary
    passed to __init__ can contain sub-dictionaries in order to group widgets together.

    Typical usage example:

    .. code-block:: python

        import my_module
        import nspyre
        from nspyre import nspyreApp
        from nspyre import MainWidget

        # Create Qt application and apply nspyre visual settings.
        app = nspyreApp()

        # Create the GUI.
        main_widget = MainWidget({
            'Experiments': {
                'ODMR': MainWidgetItem(my_module, 'ODMRWidget'),
            },
            'Plot': MainWidgetItem(nspyre.gui.widgets.flex_line_plot, 'FlexLinePlotWidget'),
            'Data': {
                'Save': MainWidgetItem(nspyre.gui.widgets.save_widget, 'SaveWidget'),
                'Load': MainWidgetItem(nspyre.gui.widgets.load_widget, 'LoadWidget'),
            }
        })
        main_widget.show()
        # Run the GUI event loop.
        app.exec()

    """

    def __init__(self, widgets, font_size='18px'):
        """
        Args:
            widgets: Dictionary - see example usage for the required form.
            font_size: Dock label font size as a string (e.g. '14px').
        """
        super().__init__()

        # delete any children Qt widgets when this widget is closed
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # window settings
        self.setWindowTitle('nspyre')
        self.resize(1200, 700)
        self.font_size = font_size

        # dict of available widgets
        self.widgets = widgets

        # dock area to view the widgets
        self.dock_area = DockArea()

        # make a GUI element to show all the available widgets
        self.tree_widget = QtWidgets.QTreeView()
        self.tree_widget.setHeaderHidden(True)
        tree_model = QtGui.QStandardItemModel()
        tree_root_node = tree_model.invisibleRootItem()

        # recursive function to parse through the user supplied widgets and add
        # them to the tree widget
        def parse_widgets(w, parent):
            for name, value in w.items():
                if isinstance(value, MainWidgetItem):
                    # leaf node
                    parent.appendRow(_MainWidgetItem(name, value))
                elif isinstance(value, dict):
                    # non-leaf node
                    node = _MainWidgetItemContainer(name)
                    parent.appendRow(node)
                    parse_widgets(value, node)
                else:
                    raise ValueError(
                        'Value in widgets dictionary must be a MainWidgetItem or another dictionary containing MainWidgetItem.'
                    )

        parse_widgets(widgets, tree_root_node)
        self.tree_widget.setModel(tree_model)
        self.tree_widget.collapseAll()
        self.tree_widget.doubleClicked.connect(self._tree_item_double_click)

        # Qt button that loads a widget from the widget list when clicked
        load_button = QtWidgets.QPushButton('Load')
        # run the load widget method on button press
        load_button.clicked.connect(self._load_widget_clicked)

        # Qt layout that arranges the widget list and load button vertically
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.tree_widget)
        main_layout.addWidget(load_button)
        # Dummy widget containing the layout
        widget_tree_container = QtWidgets.QWidget()
        widget_tree_container.setLayout(main_layout)

        # add the widget list to the dock area
        widget_list_dock = self._dock_widget(widget_tree_container, name='Widgets')
        # set size relative to other docks
        widget_list_dock.setStretch(20, 1)

        # add the snake logo to the dock area
        logo_widget = sssss()
        self.logo_dock = self._dock_widget(logo_widget, name='snake')
        self.logo_dock.hideTitleBar()
        self.logo_dock.setStretch(80, 1)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.dock_area)
        self.setLayout(layout)

    def _tree_item_double_click(self, model_index):
        tree_widget_item = self.tree_widget.model().itemFromIndex(model_index)
        self._load_widget(tree_widget_item)

    def _load_widget_clicked(self):
        # get the currently selected tree index
        selected_tree_index = self.tree_widget.selectedIndexes()[0]
        # retrieve the item
        tree_widget_item = self.tree_widget.model().itemFromIndex(selected_tree_index)
        self._load_widget(tree_widget_item)

    def _load_widget(self, tree_widget_item):
        """Loads the QWidget corresponding to the given tree item and add it to
        the :code:`DockArea`."""
        if isinstance(tree_widget_item, _MainWidgetItemContainer):
            # do nothing if the user tried to load a container class item
            return

        widget_name = tree_widget_item.name
        widget_module = tree_widget_item.main_widget_item.module
        widget_class_name = tree_widget_item.main_widget_item.cls
        widget_args = tree_widget_item.main_widget_item.args
        widget_kwargs = tree_widget_item.main_widget_item.kwargs

        # reload the module at runtime in case any changes were made to the code
        widget_module = reload(widget_module)
        widget_class = getattr(widget_module, widget_class_name)
        # create an instance of the widget class
        widget = widget_class(*widget_args, **widget_kwargs)
        # add the widget to the GUI
        dock = self._dock_widget(widget, name=widget_name, closable=True)
        # set the dock stretch factor
        # see https://pyqtgraph.readthedocs.io/en/latest/api_reference/dockarea.html
        stretch = tree_widget_item.main_widget_item.stretch
        if stretch is not None:
            dock.setStretch(*stretch)

    def _dock_widget(self, widget, *args, **kwargs):
        """Create a new dock for the given widget and add it to the :code:`DockArea`."""
        # if the logo dock is there, remove it
        try:
            if self.logo_dock is not None:
                self.logo_dock.close()
                self.logo_dock = None
        except AttributeError:
            # if logo_dock hasn't been defined yet
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
        # make sure the widget gets deleted when the dock is closed by the user
        dock.sigClosed.connect(widget.deleteLater)
        self.dock_area.addDock(dock, 'right')

        return dock
