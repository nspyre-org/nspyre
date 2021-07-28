from PyQt5 import QtWidgets
import pyqtgraph as pg
from collections import OrderedDict

from nspyre.definitions import Q_
from nspyre.misc import RangeDict

from .spinbox import SpinBox


class ParamWidget(QtWidgets.QWidget):

    def __init__(self, parameters, parent=None):
        super().__init__(parent=parent)
        self.parameters = parameters
        self.init_ui()
        return

    def init_ui(self):
        layout = QtWidgets.QFormLayout()
        getter_methods = dict()
        setter_methods = dict()
        for parameter_name, parameter_opts in self.parameters.items():
            typ = parameter_opts.get('type', str)
            default = parameter_opts.get('default')
            if typ == str:
                w = QtWidgets.QLineEdit(default)
                activation_method = w.text
                getter_method = w.text
                setter_method = w.setText
            elif typ == int or typ == float:
                default_opts = {
                    # 'suffix': parameter_opts.get('units', ''),
                    # 'siPrefix': False,
                    'dec': True,
                    'int': typ == int,
                    'minStep': 1 if typ == int else 0.1,
                    'step': 1 if typ == int else 0.1,
                    'bounds': [None, None],
                    'decimals': 8,
                }
                opts = dict()
                if parameter_opts.get('nonnegative', False):
                    opts['bounds'] = [0, None]
                if typ == int and parameter_opts.get('positive', False):
                    opts['bounds'] = [1, None]
                for k in default_opts.keys():
                    opts[k] = parameter_opts.get(k, default_opts[k])

                w = SpinBox(unit=parameter_opts.get('units'), **opts)
                # w = pg.SpinBox(**opts)
                w.setValue(default)
                # getter_method = w.value
                getter_method = w.unit_value
                setter_method = w.setValue
            elif typ == bool:
                w = QtWidgets.QCheckBox()
                getter_method = w.isChecked
                setter_method = w.setChecked
                default = default if default is not None else False
                w.setChecked(default)
            elif typ == object:
                w = parameter_opts['widget']
                getter_method = parameter_opts['getter']
                setter_method = parameter_opts.get('setter', None)
            elif typ == range:
                w = Rangespace(units=parameter_opts.get('units'))
                getter_method = w.get
                setter_method = w.set
                if not default is None:
                    w.set(default)
            elif typ == list:
                w = pg.ComboBox()
                items = parameter_opts.get('items')
                if type(items) == list:
                    w.setItems(items)
                else:
                    raise ValueError('items must be specified and of type list to add a list type entry to ParamWidget')
                getter_method = w.value
                setter_method = w.setText
                if not default is None:
                    try:
                        w.setText(default)
                    except ValueError:
                        pass
            elif typ == dict:
                w = pg.ComboBox()
                items = parameter_opts.get('items')
                if type(items) == dict:
                    w.setItems(items)
                else:
                    raise ValueError('items must be specified and of type dict to add a dict type entry to ParamWidget')
                getter_method = w.value
                setter_method = w.setValue
                if not default is None:
                    w.setValue(default)

            layout.addRow(parameter_name, w)
            getter_methods[parameter_name] = getter_method
            setter_methods[parameter_name] = setter_method
        self.getter_methods = getter_methods
        self.setter_methods = setter_methods
        self.setLayout(layout)
        return

    def get(self):
        return {name: method() for name, method in self.getter_methods.items()}

    def set(self, **kwargs):
        for k, v in kwargs.items():
            setter = self.setter_methods[k]
            if setter is not None:
                setter(v)
        return

    def save_state(self):
        state = self.get()
        return state

    def load_state(self, state):
        self.set(**state)
