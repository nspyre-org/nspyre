"""
GUI for controlling the subsystems of the biosensing2 setup.

Copyright (c) 2022, Jacob Feder
All rights reserved.
"""
import logging

from pyqtgraph.Qt import QtWidgets
from pyqtgraph.Qt import QtGui

from bs2.drivers.meta_driver import Subsystem

logger = logging.getLogger(__name__)

class SubsystemTreeItem(QtGui.QStandardItem):
    """A leaf node in the QTreeView of the meta driver GUI which contains a 
    Subsystem."""
    def __init__(self, subsys: Subsystem, booted_color: QtGui.QColor=QtGui.QColor(127, 179, 0), shutdown_color: QtGui.QColor=QtGui.QColor(156, 0, 0)):
        """
        Args:
            subsys: instance of Subsystem
        """
        super().__init__()
        self.subsys = subsys
        self.setEditable(False)
        self.setText(subsys.name)
        self.booted_color = booted_color
        self.shutdown_color = shutdown_color

    def state_changed(self, state):
        """Change the item color based on the new subsystem state."""
        if state:
            self.setBackground(self.booted_color)
        else:
            self.setBackground(self.shutdown_color)

class SubsystemsWidget(QtWidgets.QWidget):
    """Qt widget for controlling the BS2 subsystems."""

    def __init__(self, driver):
        """
        Args:
            driver: an instance of the meta driver
        """
        super().__init__()

        self.drv = driver

        # top level layout
        layout = QtWidgets.QVBoxLayout()

        # make a GUI element to show all the available widgets
        self.subsys_tree_widget = QtWidgets.QTreeView()
        self.subsys_tree_widget.setHeaderHidden(True)
        tree_model = QtGui.QStandardItemModel()
        tree_root_node = tree_model.invisibleRootItem()
        # recursive function to parse through the subsystems and add 
        # them to the tree widget
        def parse_subsystems(subsys, parent):
            # make a tree item to represent this subsystem
            node = SubsystemTreeItem(subsys)
            # set the initial color of the subsystem in the GUI
            node.state_changed(subsys.booted)
            # any subsequent changes to the subsystem state will trigger a color update
            subsys.state_changed.connect(node.state_changed)
            # add the node to the tree
            parent.appendRow(node)
            # add all dependency nodes to the tree
            for s in subsys.dependencies:
                parse_subsystems(s, node)
        parse_subsystems(self.drv.subsystems['bs2'], tree_root_node)
        parse_subsystems(self.drv.subsystems['other'], tree_root_node)
        self.subsys_tree_widget.setModel(tree_model)
        self.subsys_tree_widget.collapseAll()
        self.subsys_tree_widget.doubleClicked.connect(self.tree_item_double_click)

        buttons_layout = QtWidgets.QGridLayout()
        layout_row = 0

        # boot subsystem button
        self.boot_button = QtWidgets.QPushButton('Boot')
        self.boot_button.clicked.connect(self.boot_clicked)
        buttons_layout.addWidget(self.boot_button, layout_row, 0)

        # boot dependencies checkbox
        self.boot_dependencies_checkbox = QtWidgets.QCheckBox()
        self.boot_dependencies_checkbox.setChecked(True)
        self.boot_dependencies_checkbox.setText('Boot Dependencies')
        buttons_layout.addWidget(self.boot_dependencies_checkbox, layout_row, 1)

        layout_row += 1

        # shutdown subsystem button
        self.shutdown_button = QtWidgets.QPushButton('Shutdown')
        self.shutdown_button.clicked.connect(self.shutdown_clicked)
        buttons_layout.addWidget(self.shutdown_button, layout_row, 0)

        # shutdown dependencies checkbox
        self.shutdown_dependencies_checkbox = QtWidgets.QCheckBox()
        self.shutdown_dependencies_checkbox.setChecked(True)
        self.shutdown_dependencies_checkbox.setText('Shutdown Dependencies')
        buttons_layout.addWidget(self.shutdown_dependencies_checkbox, layout_row, 1)

        layout_row += 1

        # take up any additional space in the final column with padding
        buttons_layout.setColumnStretch(2, 1)
        # take up any additional space in the final row with padding
        buttons_layout.setRowStretch(layout_row, 1)

        # window layout
        layout.addWidget(self.subsys_tree_widget)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def tree_item_double_click(self, model_index):
        tree_subsys_item = self.subsys_tree_widget.model().itemFromIndex(model_index)
        self.boot(tree_subsys_item.subsys)

    def boot_clicked(self):
        # get the currently selected tree index
        selected_tree_index = self.subsys_tree_widget.selectedIndexes()[0]
        # retrieve the item
        tree_subsys_item = self.subsys_tree_widget.model().itemFromIndex(selected_tree_index)
        self.boot(tree_subsys_item.subsys)

    def shutdown_clicked(self):
        # get the currently selected tree index
        selected_tree_index = self.subsys_tree_widget.selectedIndexes()[0]
        # retrieve the item
        tree_subsys_item = self.subsys_tree_widget.model().itemFromIndex(selected_tree_index)
        shutdown_dependencies = self.shutdown_dependencies_checkbox.isChecked()
        tree_subsys_item.subsys.shutdown(shutdown_dependencies=shutdown_dependencies)

    def boot(self, subsys):
        boot_dependencies = self.boot_dependencies_checkbox.isChecked()
        subsys.boot(boot_dependencies=boot_dependencies)
