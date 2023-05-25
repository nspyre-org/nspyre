"""Widget that generates a simple GUI that allows the user to enter a set of
parameters.
"""
from typing import Dict
from typing import Optional

from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtWidgets


class ParamsWidget(QtWidgets.QWidget):
    """Qt widget containing a set of GUI elements for the user to enter experiment \
    parameters into.

    Typical usage example:

    .. code-block:: python

        from pyqtgraph import SpinBox
        from pyqtgraph.Qt import QtWidgets

        class MyWidget(QtWidgets.QWidget)
            def __init__(self):
                super().__init__()
                self.params_widget = ParamsWidget({
                    'start_freq': {
                        'display_text': 'Start Frequency',
                        'widget': SpinBox(
                            value=3e9,
                            suffix='Hz',
                            siPrefix=True,
                            bounds=(100e3, 10e9),
                            dec=True,
                        ),
                    },
                    'stop_freq': {
                        'display_text': 'Stop Frequency',
                        'widget': SpinBox(
                            value=4e9,
                            suffix='Hz',
                            siPrefix=True,
                            bounds=(100e3, 10e9),
                            dec=True,
                        ),
                    },
                    'num_points': {
                        'display_text': 'Number of Scan Points',
                        'widget': \
SpinBox(value=100, int=True, bounds=(1, None), dec=True),
                    },
                    'iterations': {
                        'display_text': 'Number of Experiment Repeats',
                        'widget': \
SpinBox(value=20, int=True, bounds=(1, None), dec=True),
                    },
                    'dataset': {
                        'display_text': 'Data Set',
                        'widget': QtWidgets.QLineEdit('odmr'),
                    },
                })

            ...

            def doSomething(self):
                print(f'Scanning from = {self.params_widget.start_freq} Hz to = \
{self.params_widget.stop_freq} Hz.'

    """

    def __init__(
        self, params_config: Dict, get_param_value_funs: Optional[Dict] = None
    ):
        """
        Args:
            params_config: Dictionary mapping parameter names to a parameter
                configuration dictionary, which should contain:

                - :code:`widget`: QWidget instance that represents the parameter
                - :code:`display_text` [optional]: parameter text label

            get_param_value_funs: Dictionary mapping Python classes to a
                function that takes an instance of that class and returns its
                value. This can be used to show ParamsWidget how to handle new
                QWidgets. There is built-in support for pyqtgraph SpinBox,
                QLineEdit, QComboBox, QCheckBox. E.g.:

                .. code-block:: python

                    def get_lineedit_val(lineedit):
                        return lineedit.text()

                    pw = ParamsWidget({
                                'dataset': {
                                    'display_text': 'Data Set',
                                    'widget': QtWidgets.QLineEdit('odmr'),
                                },
                                ...
                            },
                            get_param_value_funs={QLineEdit: get_lineedit_val}
                        )

        """
        super().__init__()
        self.params_config = params_config
        self.widgets = {}

        # getter functions of GUI parameter widgets
        if get_param_value_funs is None:
            self.get_param_value_funs = {}
        else:
            self.get_param_value_funs = get_param_value_funs
        # pyqtgraph SpinBox
        if SpinBox not in self.get_param_value_funs:

            def get_spinbox_val(spinbox):
                return spinbox.value()

            self.get_param_value_funs[SpinBox] = get_spinbox_val
        # QLineEdit
        if QtWidgets.QLineEdit not in self.get_param_value_funs:

            def get_lineedit_val(lineedit):
                return lineedit.text()

            self.get_param_value_funs[QtWidgets.QLineEdit] = get_lineedit_val
        # QComboBox
        if QtWidgets.QComboBox not in self.get_param_value_funs:

            def get_combobox_val(combobox):
                idx = combobox.currentIndex()
                return combobox.itemText(idx)

            self.get_param_value_funs[QtWidgets.QComboBox] = get_combobox_val
        # QCheckBox
        if QtWidgets.QCheckBox not in self.get_param_value_funs:

            def get_combobox_val(checkbox):
                return checkbox.isChecked()

            self.get_param_value_funs[QtWidgets.QCheckBox] = get_combobox_val

        # layout
        layout = QtWidgets.QGridLayout()
        layout_row = 0

        # add widgets to the layout
        for p in self.params_config:
            # create parameter label
            label = QtWidgets.QLabel()
            # set minimum size for label so that other widget uses the rest of the space
            label.setSizePolicy(
                QtWidgets.QSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Fixed,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
            )
            # TODO align text to right side
            # label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            try:
                display_text = self.params_config[p]['display_text']
            except KeyError:
                label.setText(p)
            else:
                label.setText(display_text)
            layout.addWidget(label, layout_row, 0)

            # retrive the QWidget
            try:
                self.widgets[p] = self.params_config[p]['widget']
            except KeyError as err:
                raise ValueError(
                    f'parameter [{p}] does not have a "widget" key'
                ) from err
            if not isinstance(self.widgets[p], QtWidgets.QWidget):
                raise ValueError(f'parameter [{p}] widget is not a QWidget')
            # set a default min width
            self.widgets[p].setMinimumWidth(100)
            # add the QWidget to the layout
            layout.addWidget(self.widgets[p], layout_row, 1)
            layout_row += 1

        self.setLayout(layout)

    def all_params(self):
        """Return the current value of all user parameters as a dictionary."""
        all_params = {}
        for p in self.params_config:
            all_params[p] = getattr(self, p)
        return all_params

    def __getattr__(self, attr: str):
        """Allow easy access to the parameter values."""
        if attr in self.params_config:
            widget = self.params_config[attr]['widget']
            try:
                fun = self.get_param_value_funs[type(widget)]
            except KeyError as err:
                raise ValueError(
                    f'Parameter [{attr}] has no function for retrieving its value '
                    'from the GUI. This should be set using the "get_param_value_funs" '
                    'in the ParamsWidget constructor.'
                ) from err
            else:
                return fun(widget)
        else:
            # raise the default python error when an attribute isn't found
            return self.__getattribute__(attr)
