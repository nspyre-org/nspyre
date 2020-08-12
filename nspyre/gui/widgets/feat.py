from collections import OrderedDict, Iterable

# 3rd party
from PyQt5 import QtWidgets, QtCore
from pyqtgraph import ComboBox

# nspyre
from nspyre.gui.widgets.spinbox import SpinBox
from nspyre.definitions import Q_

def get_feat_widget(feat):
    if feat['values'] is not None:
        w = ComboBoxFeatWidget(feat['values'])
    elif isinstance(feat['value'], (int, float, Q_)) or not feat['units'] is None:
            opts = dict()
            if feat['units'] is not None:
                opts['unit'] = feat['units']
            if feat['limits'] is not None:
                opts['bounds'] = feat['limits']
            opts['dec'] = True
            opts['minStep'] = 1e-3
            opts['decimals'] = 10
            if isinstance(feat['value'], int):
                opts['int'] = True
                opts['minStep'] = 1
                opts['decimals'] = 10
            w = SpinBoxFeatWidget(opts)
    elif feat['value'] is None:
        w = LineEditFeatWidget(text = 'Unknown type')
        w.set_readonly(True)
        return w
    else:
        w = LineEditFeatWidget(text = feat['value']) 

    w.set_readonly(feat['readonly'])
    if (not feat['value'] is None) and (not feat['units'] is None):
        w.setter(Q_(feat['value'], feat['units']))
    else:
        w.setter(feat['value'])
    return w

class BaseFeatWidget(QtWidgets.QWidget):

    set_requested = QtCore.pyqtSignal(object) # This signal will be triggered externally when the display value needs to be changed (argument is the new value)
    go_clicked = QtCore.pyqtSignal() # This signal will be triggered when the "go button" is clicked
    read_clicked = QtCore.pyqtSignal()  # This signal will be triggered when the "read button" is clicked

    def __init__(self, parent=None):
        #The parent class will need to generate a self.val_w a getter and a setter
        if not (hasattr(self, 'val_w') and hasattr(self, 'setter') and hasattr(self, 'getter')):
            raise NotImplementedError("This class must be subclassed and implement a value widget (<val_w>) and getter/setter methods")

        super().__init__(parent=parent)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Take care of the value widget and an external which can be triggered externally to change the value displayed
        self.val_w.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.val_w)
        self.set_requested.connect(self.setter)
        
        # Go button 
        go_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogOkButton)
        self.go_button = QtWidgets.QPushButton()
        self.go_button.setIcon(go_icon)
        self.go_button.clicked.connect(self.go_clicked)
        layout.addWidget(self.go_button)
        
        # Read button
        read_icon = self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)
        self.read_button = QtWidgets.QPushButton()
        self.read_button.setIcon(read_icon)
        self.read_button.clicked.connect(self.read_clicked)
        layout.addWidget(self.read_button)
        return

    def set_readonly(self, readonly):
        if readonly:
            self.val_w.setEnabled(False)
            self.go_button.setEnabled(False)
        else:
            self.val_w.setEnabled(True)
            self.go_button.setEnabled(True)
        return

class SpinBoxFeatWidget(BaseFeatWidget):

    def __init__(self, opts=None, parent=None):
        if opts is None:
            opts = dict()
        self.val_w = SpinBox(**opts)
        super().__init__(parent=parent)
        return

    def setter(self, value):
        return self.val_w.setValue(value)

    def getter(self):
        return self.val_w.getValue()

class ComboBoxFeatWidget(BaseFeatWidget):

    def __init__(self, values, parent=None):
        self.values = values
        self.val_w = ComboBox()
        if isinstance(self.values, OrderedDict):
            for key, value in self.values.items():
                self.val_w.addItem(str(key), str(value))
        elif isinstance(self.values, dict):
            for key, value in sorted(self.values.items()):
                self.val_w.addItem(str(key), str(value))
        elif isinstance(self.values, set):
            for value in sorted(self.values):
                self.val_w.addItem(str(value), str(value))
        elif isinstance(self.values, Iterable):
            for value in self.values:
                self.val_w.addItem(str(value), str(value))
        else:
            raise TypeError('invalid type encountered while populating values')
        super().__init__(parent=parent)
        return

    def setter(self, value):
        index = self.val_w.findText(str(value))
        self.val_w.setCurrentIndex(index)
        return

    def getter(self):
        index = self.val_w.currentIndex()
        values = self.values
        if isinstance(values, OrderedDict):
            key = list(values.keys())[index]
        elif isinstance(values, dict):
            key = list(sorted(values.keys()))[index]
        elif isinstance(values, set):
            key = list(sorted(values))[index]
        else:
            key = values[index]
        return key

class LineEditFeatWidget(BaseFeatWidget):

    def __init__(self, parent=None, text=None):
        self.val_w = QtWidgets.QLineEdit()
        super().__init__(parent=parent)
        return

    def setter(self, value):
        self.val_w.setText(str(value))
        return

    def getter(self):
        value = self.val_w.text()
        return value
