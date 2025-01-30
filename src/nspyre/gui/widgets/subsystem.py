from collections.abc import Iterable

from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

from ...extras.subsystem import Subsystem

DEFAULT_BOOTED_COLOR = QtGui.QColor(127, 179, 0)
"""QColor of "booted" items in QTreeView of subsystems."""
DEFAULT_SHUTDOWN_COLOR = QtGui.QColor(156, 0, 0)
"""QColor of "shutdown" items in QTreeView of subsystems."""


class _SubsystemTreeItem(QtGui.QStandardItem):
    """A leaf node in the QTreeView of the subsystems GUI."""

    def __init__(
        self,
        subsys: Subsystem,
        booted_color: QtGui.QColor = DEFAULT_BOOTED_COLOR,
        shutdown_color: QtGui.QColor = DEFAULT_SHUTDOWN_COLOR,
    ):
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

    def booted(self):
        """Change the item color to reflect booted state."""
        self.setBackground(self.booted_color)

    def shutdown(self):
        """Change the item color to reflect shutdown state."""
        self.setBackground(self.shutdown_color)


class SubsystemsWidget(QtWidgets.QWidget):
    """Qt widget for booting and shutting down subsystems."""

    def __init__(self, subsystems: Iterable[Subsystem]):
        """
        Args:
            subsystems: An iterable containing
                :py:class:`~nspyre.extras.subsystem.Subsystem` objects.
        """
        super().__init__()

        # top level layout
        layout = QtWidgets.QVBoxLayout()

        # make a GUI element to show all the available subsystems
        self.subsys_tree_widget = QtWidgets.QTreeView()
        self.subsys_tree_widget.setHeaderHidden(True)
        tree_model = QtGui.QStandardItemModel()
        tree_root_node = tree_model.invisibleRootItem()

        # recursive function to parse through the subsystems and add them to the
        # tree widget
        def parse_subsystems(subsys, parent):
            # make a tree item to represent this subsystem
            node = _SubsystemTreeItem(subsys)
            # set the initial color of the subsystem in the GUI
            if subsys.booted:
                node.booted()
            else:
                node.shutdown()
            # any subsequent changes to the subsystem state will trigger a color update
            subsys.booted_sig.connect(node.booted)
            subsys.shutdown_sig.connect(node.shutdown)
            # add the node to the tree
            parent.appendRow(node)
            # add all dependency nodes to the tree
            for s in subsys.dependencies:
                parse_subsystems(s, node)

        # add all of the subsystems to the tree
        for s in subsystems:
            parse_subsystems(s, tree_root_node)
        self.subsys_tree_widget.setModel(tree_model)
        self.subsys_tree_widget.collapseAll()
        self.subsys_tree_widget.doubleClicked.connect(self._tree_item_double_click)

        buttons_layout = QtWidgets.QGridLayout()
        layout_row = 0

        # boot subsystem button
        self.boot_button = QtWidgets.QPushButton('Boot')
        self.boot_button.clicked.connect(self._boot_clicked)
        buttons_layout.addWidget(self.boot_button, layout_row, 0)

        # boot dependencies checkbox
        self.boot_dependencies_checkbox = QtWidgets.QCheckBox()
        self.boot_dependencies_checkbox.setChecked(True)
        self.boot_dependencies_checkbox.setText('Boot Dependencies')
        buttons_layout.addWidget(self.boot_dependencies_checkbox, layout_row, 1)

        layout_row += 1

        # shutdown subsystem button
        self.shutdown_button = QtWidgets.QPushButton('Shutdown')
        self.shutdown_button.clicked.connect(self._shutdown_clicked)
        buttons_layout.addWidget(self.shutdown_button, layout_row, 0)

        # shutdown dependencies checkbox
        self.shutdown_dependencies_checkbox = QtWidgets.QCheckBox()
        self.shutdown_dependencies_checkbox.setChecked(False)
        self.shutdown_dependencies_checkbox.setText('Shutdown Dependencies')
        buttons_layout.addWidget(self.shutdown_dependencies_checkbox, layout_row, 1)

        layout_row += 1

        # shutdown dependencies checkbox
        self.force_shutdown_checkbox = QtWidgets.QCheckBox()
        self.force_shutdown_checkbox.setChecked(False)
        self.force_shutdown_checkbox.setText('Force Shutdown')
        buttons_layout.addWidget(self.force_shutdown_checkbox, layout_row, 1)

        layout_row += 1

        # take up any additional space in the final column with padding
        buttons_layout.setColumnStretch(2, 1)
        # take up any additional space in the final row with padding
        buttons_layout.setRowStretch(layout_row, 1)

        # window layout
        layout.addWidget(self.subsys_tree_widget)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def _tree_item_double_click(self, model_index):
        tree_subsys_item = self.subsys_tree_widget.model().itemFromIndex(model_index)
        self._boot(tree_subsys_item.subsys)

    def _boot_clicked(self):
        # get the currently selected tree index
        selected_tree_index = self.subsys_tree_widget.selectedIndexes()[0]
        # retrieve the item
        tree_subsys_item = self.subsys_tree_widget.model().itemFromIndex(
            selected_tree_index
        )
        self._boot(tree_subsys_item.subsys)

    def _shutdown_clicked(self):
        # get the currently selected tree index
        selected_tree_index = self.subsys_tree_widget.selectedIndexes()[0]
        # retrieve the item
        tree_subsys_item = self.subsys_tree_widget.model().itemFromIndex(
            selected_tree_index
        )
        shutdown_dependencies = self.shutdown_dependencies_checkbox.isChecked()
        force = self.force_shutdown_checkbox.isChecked()
        tree_subsys_item.subsys.shutdown(
            shutdown_dependencies=shutdown_dependencies, force=force
        )

    def _boot(self, subsys):
        boot_dependencies = self.boot_dependencies_checkbox.isChecked()
        subsys.boot(boot_dependencies=boot_dependencies)
