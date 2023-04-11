from typing import Dict

from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

class LayoutTreeNode:
    def __init__(self, layout, children):
        self.layout = layout
        self.children = children

    def __getattr__(self, attr):
        if attr in self.children:
            return self.children[attr]
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)

def tree_layout(config):
    """Arrange a tree of provided widgets into corresponding Qt layout objects.

    Args:
        config: Tree of dictionaries describing the layout structure.
            Each dictionary (node) must contain a :code:`'type'` key and a 
            :code:`'subs'` key. The value associated with :code:`'type'` 
            should be a :code:`QtWidgets.QLayout`. The value associated
            with :code:`'subs'` should be a list containing QWidgets, 
            QLayouts, and more sub-dictionaries with the given structure.

    Example usage:

    .. code-block:: python

        l1 = QtWidgets.QLabel('Label1')
        l2 = QtWidgets.QLabel('Label2')
        l3 = QtWidgets.QLabel('Label3')
        l4 = QtWidgets.QLabel('Label4')
        l5 = QtWidgets.QLabel('Label5')
        l6 = QtWidgets.QLabel('Label6')
        layout_config = {
        'type': QtWidgets.QVBoxLayout,
        'l1': l1,
        'l2': l2,
        'sub': 
            {'type': QtWidgets.QHBoxLayout,
            'subs': [
                l3,
                l4,
                {
                    'type': QtWidgets.QVBoxLayout,
                    'subs': [
                    l5,
                    l6,
                ]}
            ]}
        ]}
        layout = arrange_layout(layout_config)


    Raises:
        ValueError: Invalid arguments.
    """

    try:
        layout_class = config.pop('type')
    except KeyError as err:
        raise ValueError('All entries must contain a "type" key.')

    if not issubclass(layout_class, QtWidgets.QLayout):
        raise ValueError('Value associated with "type" must be a QtWidgets.QLayout.')

    layout = layout_class()
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
