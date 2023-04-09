from typing import Dict

from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

def arrange_layout(config):
    """Arrange a tree of provided widgets into corresponding Qt layout objects.

    Args:
        config: Dictionary containing a tree describing the layout structure.
            Each dictionary must contain a :code:`'type'` key and a 
            :code:`'subs'` key. The value associated with :code:`'type'` 
            should be a :code:`QtWidgets.QLayout`. The value associated
            with :code:`'subs'` should be a list containing QWidgets, 
            QLayouts, and more sub-dictionaries with the given structure.

    Raises:
        ValueError: Invalid arguments.
    """

    try:
        layout_class = config['type']
    except KeyError as err:
        raise ValueError('All config dictionary entries must contain a "type" key.')

    if not issubclass(layout_class, QtWidgets.QLayout):
        raise ValueError('Value associated with "type" must be a QtWidgets.QLayout.')

    layout = layout_class()

    try:
        subs = config['subs']
    except KeyError as err:
        raise ValueError('All config dictionary entries must contain a "subs" key.')
    
    if not isinstance(subs, list):
        raise ValueError('Value associated with "subs" must be a list.')

    for w in subs:
        if isinstance(w, QtWidgets.QWidget):
            layout.addWidget(w)
        elif isinstance(w, QtWidgets.QLayout):
            layout.addLayout(w)
        elif isinstance(w, dict):
            layout.addLayout(arrange_layout(w))
        else:
            raise ValueError('subs list may only contain QtWidget, QLayout, or dict.')

    return layout