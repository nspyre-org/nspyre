from typing import Dict

from pyqtgraph.Qt import QtWidgets


class LayoutTreeNode:
    """A node in the tree returned by :py:func:`tree_layout`."""

    def __init__(self, layout: QtWidgets.QLayout, children: dict):
        """Children can be accessed with dot notation - see example in :py:func:`tree_layout`.

        Args:
            layout: QLayout object for this node.
            children: Dict with string keys mapped to values of either 
                :code:`QtWidgets.QWidget`, :code:`QtWidgets.QLayout`, or :py:class:`~nspyre.gui.widgets.layout.LayoutTreeNode`.
        """
        self.layout = layout
        """Same as 'layout' argument."""
        self.children = children
        """Same as 'children' argument."""

    def __getattr__(self, attr):
        if attr in self.children:
            return self.children[attr]
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)


def tree_layout(config: Dict) -> LayoutTreeNode:
    """Arrange a tree of provided widgets and layouts into corresponding Qt layout objects.

    Example usage:

    .. code-block:: python

        label1 = QtWidgets.QLabel('Label1')
        label2 = QtWidgets.QLabel('Label2')
        label3 = QtWidgets.QLabel('Label3')
        label4 = QtWidgets.QLabel('Label4')
        label5 = QtWidgets.QLabel('Label5')
        label6 = QtWidgets.QLabel('Label6')
        layout_config = {
            'type': QtWidgets.QVBoxLayout,
            'l1': label1,
            'l2': label2,
            'sub_layout': {
                'type': QtWidgets.QHBoxLayout,
                'l3': label3,
                'l4': label4,
                'sub_sub_layout': {
                    'type': QtWidgets.QVBoxLayout,
                    'l5': label5,
                    'l6': label6,
                }
            }
        }
        tree_root = tree_layout(layout_config)
        print(tree_root.l1.text())
        print(tree_root.sub_layout.sub_sub_layout.l5.text())

    Args:
        config: Tree of dictionaries describing the layout structure.
            Each dictionary (node) must contain a :code:`'type'` key. The value 
            associated with :code:`'type'` should be a :code:`QtWidgets.QLayout`. 
            All other keys/values should be a string mapping to either a 
            :code:`QtWidgets.QLayout`, :code:`QtWidgets.QWidget`, or another 
            dictionary with the given structure.

    Raises:
        ValueError: Invalid arguments.

    Returns:
        The layout root node.
    """

    try:
        layout_class = config.pop('type')
    except KeyError as err:
        raise ValueError('All entries must contain a "type" key.') from err

    if not issubclass(layout_class, QtWidgets.QLayout):
        raise ValueError('Value associated with "type" must be a QtWidgets.QLayout.')

    try:
        layout = layout_class()
    except Exception as err:
        raise Exception(f'Failed creating instance of {layout_class}.') from err

    children = {}

    for child_name in config:
        child_object = config[child_name]
        if isinstance(child_object, QtWidgets.QWidget):
            layout.addWidget(child_object)
        elif isinstance(child_object, QtWidgets.QLayout):
            layout.addLayout(child_object)
        elif isinstance(child_object, dict):
            child_object = tree_layout(child_object)
            layout.addLayout(child_object.layout)
        else:
            raise ValueError('May only contain QtWidget, QLayout, or dict.')
        children[child_name] = child_object

    return LayoutTreeNode(layout, children)
