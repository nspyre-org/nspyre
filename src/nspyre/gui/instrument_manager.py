"""The class defining the NSpyre Instrument Manager MainWindow.

The InstrumentManagerWindow class is the main GUI window for viewing the live
state and settings of the hardware devices connected to an NSpyre InstrumentServer.
It is defined by the QtWidgets.QMainWindow subclass from Qt and consists of a
QTreeWidget and subsequent QTreeWidgetItem(s) for displaying the attributes of
each device located on each connected Instrument Server. It is also responsible
for creating and connecting all the callback functions to the device drivers'
PySignal.Signal(s) for updating it's own GUI QtWidgets.QtWidget(s) in real-time.
i.e. QComboBox, QLineEdit, SpinBox, etc.

From the Qt documentation:
The QMainWindow class provides a main application window, with a menu bar, dock
windows (e.g. for toolbars), and a status bar. Main windows are most often used to
provide menus, toolbars and a status bar around a large central widget, such as a
text edit, drawing canvas or QWorkspace (for MDI applications). QMainWindow is
usually subclassed since this makes it easier to encapsulate the central widget,
menus and toolbars as well as the window's state. Subclassing makes it possible to
create the slots that are called when the user clicks menu items or toolbar buttons.

  Typical usage example:

  app = app.NSpyreApp([sys.argv])
  pyqtgraph._connectCleanup()
  with ..inserv.gateway.InservGateway() as isg:
      window = main_window.InstrumentManagerWindow(isg)
      sys.exit(app.exec())

Copyright (c) 2020, Alexandre Bourassa, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import functools
import inspect
import logging

from pimpmyclass.helpers import DictPropertyNameKey
from PyQt5.QtCore import QEvent, QObject, QSize, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QCursor, QFont
from PyQt5.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
                             QPushButton, QToolTip, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
from pyqtgraph import _connectCleanup as pyqtgraph_connectCleanup
from pyqtgraph import SpinBox as pyqtgraph_SpinBox, ValueLabel as pyqtgraph_ValueLabel
from pint.util import infer_base_unit

from nspyre.config.config_files import load_meta_config
from nspyre.definitions import Q_, CLIENT_META_CONFIG_PATH
from nspyre.errors import InstrumentManagerError
from nspyre.inserv.gateway import InservGateway

__all__ = []

logger = logging.getLogger(__name__)

ROW_QSIZE = QSize(79, 23)
UPDATE_HEX_COLOR = '#1CE33D'
UPDATE_DISPLAY_TIME = 350
REFRESH_PROGRESS_HEX_COLOR = '#2E5E9B'


def disable_widget_scroll_wheel_event(control: QWidget) -> None:
    """Convenience function to prevent a scroll wheel event from affecting a widget unless:
    1. The widget has focus
    2. The cursor is on the widget
    """
    control.setFocusPolicy(Qt.StrongFocus)
    control.installEventFilter(MouseWheelWidgetAdjustmentGuard(control))


class MouseWheelWidgetAdjustmentGuard(QObject):
    """This QObject class contains a Qt eventFilter method to ignore mouse scroll
     wheel inputs. This is useful to apply on widgets for which:
     a) you don't want the scroll wheel to change values ever; or
     b) the widget is inside a QAbstractScrollArea and preventing the scroll wheel from panning
     the area correctly (for this the FocusPolicy must additionally be changed to StrongFocus).
    """
    def __init__(self, parent: QObject):
        super().__init__(parent)

    def eventFilter(self, qobject: QObject, event: QEvent) -> bool:
        widget: QWidget = qobject
        if event.type() == QEvent.Wheel and not widget.hasFocus():
            event.ignore()
            return True
        return super().eventFilter(qobject, event)


class RefreshValuesThread(QThread):
    """This QThread class contains a run method for use with the InstrumentManagerWindow 'refresh all' button to update
    all feat/dictfeat values in the GUI. It does the following:
    1. update the progress bar displayed while the QThread is running
    2. call each feat/dictfeat of every driver on every server to get an updated value
    3. emit a pyqtSignal with the feat/dictfeat's tuple index in the parent GUI
       getattr_func mapping list and its updated value
    """

    refresh_progress = pyqtSignal(str, float)
    value_update = pyqtSignal(int, object)

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self.mapping = parent.device_to_getattr_func_mapping

    def run(self) -> None:
        num_attributes = len(self.mapping)
        for i, mapping in enumerate(self.mapping):
            percent = float('%.5f' % (i / num_attributes))
            self.refresh_progress.emit('Please Wait... ({}/{})'.format(i, num_attributes), percent)

            # attempt to first unpack each tuple as if it is for a dictfeat, then handle for a feat
            try:
                feat_name, device, dictfeat_key = mapping[1:]
                value = getattr(device, feat_name)[dictfeat_key]
            except ValueError:
                feat_name, device = mapping[1:]
                value = getattr(device, feat_name)
            self.value_update.emit(i, value)


class pyqt_LineEdit(QLineEdit):
    """This QLineEdit class modifies the existing QLineEdit with a pyqtgraph ValueLabel so it can handle SI units in the
    same way as other pyqtgraph widgets because pyqtgraph does not have its own QLineEdit implementation.
    """

    def __init__(self, suffix, siPrefix, contents: str = None, parent: QWidget = None):
        super().__init__((contents, parent) if contents else parent)
        self.valuelabel = pyqtgraph_ValueLabel(suffix=suffix, siPrefix=siPrefix)
        self.setReadOnly(True)

    def setValue(self, value):
        self.valuelabel.setValue(value)
        self.setText(self.valuelabel.generateText())


class InstrumentManagerWindow(QMainWindow):
    """Creates a GUI interface for controlling instrument attributes
    based on a dropdown / tree structure
    the top level is the instrument servers
    the next level is the devices
    the bottom level is attributes of the devices.

     # tree of dictionaries that contains all of the instrument
     # manager GUI elements
     # the top level of the dictionary is the instrument servers
     # the next level is the devices
     # the bottom level is attributes of the devices

     e.g.               ----------self.gui----------
                       /                            \
                   server1                        server2
                  /       \                      /       \
          sig-gen1         scope1        sig-gen2         laser
          /      \        /      \      /        \       /     \
       freq     ampl    trig    din[] freq      ampl  lambda  power
     """

    def __init__(self, gateway, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('NSpyre Instrument Manager')
        # connection to the instrument servers
        self.gateway = gateway

        # set main GUI layout
        self.tree = QTreeWidget()
        self.tree.setMouseTracking(True)
        self.tree.entered.connect(self.handleItemEntered)
        self.tree.setFont(QFont('Helvetica [Cronyx]', 14))
        self.tree.setColumnCount(2)
        self.tree.setMinimumHeight(self.tree.height())
        # set all rows to have the same height.
        # this provides performance improvements to the rendering time.
        # the actual height set is determined from the first QTreeWidgetItem given.
        self.tree.setUniformRowHeights(True)

        # configure the QTreeWidget Header
        header = self.tree.header()
        header.setHidden(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        # need to set to False to correctly calculate minimum width values
        header.setStretchLastSection(False)

        # add 'refresh all' button for manually triggering a driver feat update
        self.device_to_getattr_func_mapping = list()
        self.refresh_all_button = QPushButton('Refresh All Values', self)
        self.refresh_button_color = self.refresh_all_button.palette().button().color().name()
        self.refresh_all_button.setProperty('class', 'refresh_all')
        self.refresh_all_button.clicked.connect(self._refresh_all)

        # generate gui elements and set minimum window dimensions before displaying
        self._create_widgets()
        self.tree.expandAll()
        # Adding 2pt of padding to the margin to remove horizontal scroll bar and 14pt of padding for the vertical scroll bar
        self.tree.setMinimumWidth(self.tree.columnWidth(0) + self.tree.columnWidth(1) + 2 + 14)
        self.tree.collapseAll()
        # start GUI with the servers expanded
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setExpanded(True)
        # need to set this last, otherwise minimum width values are not calculated correctly
        header.setStretchLastSection(True)

        # Set the main window layout to consist of vertical boxes.
        # The QVBoxLayout class lines up widgets vertically.
        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        layout.addWidget(self.refresh_all_button)
        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        layout.setContentsMargins(0, 0, 0, layout.getContentsMargins()[3])
        self.show()

    def handleItemEntered(self, index):
        """Manual cursor tracking so that QToolTips disappear after moving cursor off corresponding QLabel."""
        if index.isValid() and index.data(Qt.ToolTipRole):
            QToolTip.showText(QCursor.pos(), index.data(Qt.ToolTipRole),
                              self.tree.viewport(), self.tree.visualRect(index))

    @pyqtSlot(str, float)
    def update_refresh_all_button(self, string: str, percent: float) -> None:
        """Slot for receiving Signals with QThread processing progress to update GUI progress bar."""
        self.refresh_all_button.setText(string)
        stylesheet = ('min-height: 34px;'  # add 2px to accord for no border
                      'border: none;'
                      'border-radius: 4px;'
                      'background-color: qlineargradient('
                      'spread: pad, x1: 0, y1: 0, x2: 1, y2: 0,'
                      'stop: 1 {background_color},'
                      'stop: {percent} {progress_color},'
                      'stop: {delta} {background_color});'.format(
                            background_color=self.refresh_button_color,
                            percent=percent,
                            delta=percent + 0.0000001,
                            progress_color=REFRESH_PROGRESS_HEX_COLOR)
                      )
        self.refresh_all_button.setStyleSheet(stylesheet)

    @pyqtSlot(int, object)
    def update_treewidgetitem_widget(self, index, value) -> None:
        """Slot for receiving Signals with updated fict/dictfeat values to update the corresponding GUI element."""
        self.device_to_getattr_func_mapping[index][0](value, None)

    def _refresh_all_finished(self):
        """Cleanup code for 'refresh all' button once the spawned QThread has finished processing."""
        self.refresh_all_button.setText('Refresh All Values')
        self.refresh_all_button.setStyleSheet('background-color: {};'.format(self.refresh_button_color))
        for child in self.tree.children()[0].children():
            child.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.refresh_all_button.setEnabled(True)

    def _refresh_all(self):
        """Spawn a QThread to get updated values for each feat/dictfeat when the 'refresh all' button is clicked."""
        self.refresh_all_button.setEnabled(False)
        for child in self.tree.children()[0].children():
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        refresh_thread = RefreshValuesThread(self)
        refresh_thread.refresh_progress.connect(self.update_refresh_all_button)
        refresh_thread.value_update.connect(self.update_treewidgetitem_widget)
        refresh_thread.finished.connect(self._refresh_all_finished)
        refresh_thread.start()

    def _create_widgets(self):
        """Iterate over the available servers and devices, collect their
        attributes that can be modified by the instrument manager GUI, then
        populate the self.gui
        """

        # iterate over servers
        for server_name, server in self.gateway.servers().items():
            server_tree = QTreeWidgetItem(self.tree, [server_name, ''])
            server_tree.setExpanded(True)
            server_tree.setFont(0, QFont('Helvetica [Cronyx]', 15))
            # set size hint as the first server is the first QTreeWidgetItem to be added to the tree;
            # needed to appropriately set the uniform row height.
            server_tree.setSizeHint(0, ROW_QSIZE)

            # iterate over devices
            for device_name, device in server.root._devs.items():
                device_tree = QTreeWidgetItem(server_tree, [device_name, ''])
                device_tree.setExpanded(True)
                device_tree.setFont(0, QFont('Helvetica [Cronyx]', 15))

                try:
                    # handle feats
                    # This also returns dictfeats!
                    for feat_name, feat in device._lantz_feats.items():
                        # filter out any dictfeats
                        if isinstance(feat_name, DictPropertyNameKey):
                            continue
                        feat_widget, feat_getattr_func = self._generate_feat_widget(feat, feat_name, device)
                        self.device_to_getattr_func_mapping.append((feat_getattr_func, feat_name, device))
                        # we have to use a partial here because PySignal and RPyC don't
                        # play nicely if you .connect() a lambda or other function / method
                        # to PySignal
                        feat_getattr_func.__name__ = 'InstrumentManager_getattr_func'
                        getattr_partial = functools.partial(feat_getattr_func)
                        getattr_partial = functools.update_wrapper(getattr_partial, feat_getattr_func)
                        # register the feat_getattr_func() to be called when the feat changes using
                        # pimpmyclass "ObservableProperty" mixin
                        getattr(device, feat_name + '_changed').connect(getattr_partial)

                        # set formatting and add docstring information as a tooltip
                        feat_widget.setFont(QFont('Helvetica [Cronyx]', 14))
                        feat_item = QTreeWidgetItem(device_tree, [feat_name, ''])
                        tool_tip = (feat.fget.__doc__.rstrip() if feat.fget.__doc__ else '') + (
                                    '\n\n' + feat.fset.__doc__.rstrip() if feat.fset.__doc__ else '')
                        if tool_tip != '':
                            feat_item.setData(0, Qt.ToolTipRole, tool_tip)
                        self.tree.setItemWidget(feat_item, 1, feat_widget)

                    # handle dictfeats
                    for dictfeat_name, dictfeat in device._lantz_dictfeats.items():
                        # Generate a Qt gui element for a lantz dictfeat and add docstring information as a tooltip
                        dictfeat_tree = QTreeWidgetItem(device_tree, [dictfeat_name, ''])
                        tool_tip = (dictfeat.fget.__doc__.rstrip() if dictfeat.fget.__doc__ else '') + (
                                    '\n\n' + dictfeat.fset.__doc__.rstrip() if dictfeat.fset.__doc__ else '')
                        if tool_tip != '':
                            dictfeat_tree.setData(0, Qt.ToolTipRole, tool_tip)

                        # dummy 'get' of dict feat value in order to force lantz to populate
                        # its 'subproperties' this is pretty hacky
                        for feat_key in dictfeat.keys:
                            feat = dictfeat.subproperty(getattr(device, dictfeat_name).instance, feat_key)
                            feat_widget, feat_getattr_func = self._generate_feat_widget(feat, dictfeat_name, device, dictfeat_key=feat_key)
                            self.device_to_getattr_func_mapping.append((feat_getattr_func, dictfeat_name, device, feat_key))

                            feat_widget.setFont(QFont('Helvetica [Cronyx]', 14))
                            feat_item = QTreeWidgetItem(dictfeat_tree, ['{} {}'.format(dictfeat_name, feat_key), ''])
                            self.tree.setItemWidget(feat_item, 1, feat_widget)
                            if feat_key == dictfeat.keys[-1]:
                                # connect the feat_getattr() to be called when the feat changes using
                                # pimpmyclass "ObservableProperty" mixin
                                def dictfeat_getattr_func(df_tree, df_keys, getattr_func, value, old_value, key):
                                    w = self.tree.itemWidget(df_tree.child(df_keys.index(key)), 1)
                                    getattr_func(value, old_value, widget=w)

                                # we have to use a partial here because PySignal and RPyC don't
                                # play nicely if you .connect() a lambda or other function / method
                                # to PySignal
                                feat_getattr_func.__name__ = 'InstrumentManager_getattr_func'
                                getattr_partial = functools.partial(dictfeat_getattr_func, dictfeat_tree, dictfeat.keys, feat_getattr_func)
                                getattr_partial = functools.update_wrapper(getattr_partial, feat_getattr_func)
                                getattr(device, dictfeat_name + '_changed').connect(getattr_partial)

                    # handle actions
                    action_tree = None
                    for action_name, action in device._lantz_actions.items():
                        # actions that shouldn't be added to the GUI:
                        # default lantz actions, duplicated _async actions, and
                        # any actions with parameters other than class object
                        ignore_actions = ['initialize', 'finalize', 'update', 'refresh']
                        if action_name in ignore_actions or '_async' in action_name or len(inspect.getfullargspec(action._func).args) > 1:
                            continue
                        if not action_tree:
                            action_tree = QTreeWidgetItem(device_tree, ['Actions', ''])

                        action_widget = self._generate_action_widget(device, action, action_name)

                        # set formatting and add docstring information as a tooltip
                        action_widget.setFont(QFont('Helvetica [Cronyx]', 14))
                        action_item = QTreeWidgetItem(action_tree, [action_name, ''])
                        tool_tip = action.__doc__.rstrip() if action.__doc__ else None
                        if tool_tip:
                            action_item.setData(0, Qt.ToolTipRole, tool_tip)
                        self.tree.setItemWidget(action_item, 1, action_widget)
                except Exception as exc:
                    logger.error(exc)
                    # some error has occurred loading the device attributes
                    device_tree.setText(0, 'ERROR: {}'.format(device_name))
                    device_tree.setBackground(0, QColor(255, 0, 0, 150))
                    pass


    def _generate_feat_widget(self, feat, feat_name, device, dictfeat_key=None):
        """Generate a Qt GUI element for a lantz feat/dictfeat"""

        if dictfeat_key:
            ## val = dictfeat.subproperty(getattr(device, feat_name).instance, dictfeat_key)
            # val = getattr(device, feat_name)[dictfeat_key]  # .__getitem__(dictfeat_key)
            feat_value = getattr(device, feat_name)[dictfeat_key]
            # if lantz has a function pointer in df.fset, then it is writeable
            read_only = False if getattr(device, feat_name).df.fset else True
        else:
            feat_value = getattr(device, feat_name)
            read_only = False if feat.fset else True
        
        # the lantz feat has only a specific set of allowed values
        # so we make a dropdown box
        if feat._config['values']:
            if read_only:
                # use a lineedit instead of a combo box if it's read only
                widget = QLineEdit()
                widget.setText(str(feat_value))
                widget.setReadOnly(True)
                def getattr_func(value, old_value, widget=widget):
                    widget.setText(str(value))
                    widget_color = widget.palette().base().color().name()  # 'base: #191919'
                    widget.setStyleSheet('background-color: {}'.format(UPDATE_HEX_COLOR))
                    QTimer.singleShot(UPDATE_DISPLAY_TIME, lambda: widget.setStyleSheet('selection-background-color: {}'.format(widget_color)))
            else:
                widget = QComboBox()
                disable_widget_scroll_wheel_event(widget)
                # dictionary mapping the possible lantz values to str(values)
                # e.g. {'True' : True, 'False' : False}
                keymapping_dict = {}
                for k in iter(feat._config['values']):
                    keymapping_dict[str(k)] = k

                # add the possible values to the dropdown list
                widget.addItems(keymapping_dict.keys())
                widget.setCurrentIndex(list(keymapping_dict.values()).index(feat_value))

                # callback function for when the user changes the dropdown selection
                def setattr_func(value, key=None):
                    if key:
                        getattr(device, feat_name)[key] = keymapping_dict[widget.currentText()]
                    else:
                        setattr(device, feat_name, keymapping_dict[widget.currentText()])
                # call setattr_func() when the combo box value is set from the GUI
                widget.activated.connect(functools.partial(setattr_func, key=dictfeat_key))
                def sizeHint(self):
                    return ROW_QSIZE
                widget.sizeHint = sizeHint.__get__(widget, QComboBox)

                # callback function to modify the GUI when the the feat is changed externally
                def getattr_func(value, old_value, widget=widget):
                    # because the _changed is shared for all keys of the same dictfeat,
                    # we have to check to see if this was the key that was actually changed
                    widget.setCurrentIndex(list(keymapping_dict.values()).index(value))
                    widget_color = widget.palette().alternateBase().color().name()  # 'alternatebase: #353535'
                    widget.setStyleSheet('background-color: {}'.format(UPDATE_HEX_COLOR))
                    QTimer.singleShot(UPDATE_DISPLAY_TIME, lambda: widget.setStyleSheet('selection-background-color: {}'.format(widget_color)))

        # the lantz feat is some sort of numerical value, so we will
        # generate a SpinBox (number entry with increment / decrement arrow keys)
        elif isinstance(feat_value, (int, float, Q_)):
            # arguments for the SpinBox
            optional_args = {}
            
            if feat._config['units']:
                if isinstance(feat_value, Q_):
                    base_units = infer_base_unit(feat_value)
                    base_units_str = '{0.units:~}'.format(Q_(1, base_units))
                    optional_args['suffix'] = base_units_str
                    optional_args['siPrefix'] = True
                else:
                    raise Exception('Didn\'t think this could happen... '
                        'the value of a lantz feat with units isn\'t a Q_')

            if feat._config['limits']:
                if len(feat._config['limits']) == 1:
                    # only min or only max was specified e.g.
                    # (,max) or (min,)
                    try:
                        optional_args['min'] = feat._config['limits'][0]
                    except IndexError:
                        optional_args['max'] = feat._config['limits'][1]
                else:
                    # (min, max) was specified
                    optional_args['bounds'] = feat._config['limits']

            # stepping strategy (specific settings needed to get step_widget working correctly)
            optional_args['dec'] = False
            optional_args['step'] = 1
            optional_args['minStep'] = 1e-6
            # number of decimal places to display
            optional_args['decimals'] = 6
            optional_args['compactHeight'] = False
            if isinstance(feat_value, int):
                optional_args['int'] = True
                optional_args['minStep'] = 1
                # optional_args['decimals'] = 10

            if read_only:
                pyqt_widget = pyqt_LineEdit(optional_args.get('suffix', ''), optional_args.get('siPrefix', False))
            else:
                pyqt_widget = pyqtgraph_SpinBox(**optional_args)
                disable_widget_scroll_wheel_event(pyqt_widget)
                def sizeHint(self):
                    return QSize(89, 23)
                pyqt_widget.sizeHint = sizeHint.__get__(pyqt_widget, pyqtgraph_SpinBox)
                pyqt_widget.setFont(QFont('Helvetica [Cronyx]', 14))

            if isinstance(feat_value, Q_):
                pyqt_widget.setValue(feat_value.to(base_units).m)
            else:
                pyqt_widget.setValue(feat_value)
            
            if feat._config['units']:
                # callback function for when the user changes the value from the GUI
                def setattr_func(value):
                    setattr(device, feat_name, Q_(pyqt_widget.value(), base_units))
                # callback function to modify the GUI when the the feat is changed externally
                def getattr_func(value, old_value, widget=pyqt_widget):
                    if isinstance(value, Q_):
                        pyqt_widget.setValue(value.to(base_units).m)
                    else:
                        pyqt_widget.setValue(value)
                    widget_color = pyqt_widget.palette().base().color().name()  # 'base: #191919'
                    pyqt_widget.setStyleSheet('background-color: {}'.format(UPDATE_HEX_COLOR))
                    QTimer.singleShot(UPDATE_DISPLAY_TIME, lambda: pyqt_widget.setStyleSheet('selection-background-color: {}'.format(widget_color)))
            else:
                def setattr_func(value):
                    setattr(device, feat_name, pyqt_widget.value())
                def getattr_func(value, old_value, widget=pyqt_widget):
                    pyqt_widget.setValue(value)
                    widget_color = pyqt_widget.palette().base().color().name()  # 'base: #191919'
                    pyqt_widget.setStyleSheet('background-color: {}'.format(UPDATE_HEX_COLOR))
                    QTimer.singleShot(UPDATE_DISPLAY_TIME, lambda: pyqt_widget.setStyleSheet('selection-background-color: {}'.format(widget_color)))

            if read_only:
                widget = pyqt_widget
            else:
                pyqt_widget.sigValueChanged.connect(setattr_func)

                # text that says 'step'
                step_label = QLabel()
                step_label.setText('step:')

                # editable text box where the user can enter how much the feat should step by when
                # pressing the increment/decrement arrows
                step_widget = QLineEdit()
                step_widget.setFixedSize(73, 23)
                step_widget.setFont(QFont('Helvetica [Cronyx]', 14))
                if isinstance(feat_value, Q_):
                    # set the default step units to be whatever the units are for the lantz feat
                    units_str = '{0.units:~}'.format(feat_value)
                    step_widget.setText('1 ' + units_str)
                    def set_step_func(value):
                        try:
                            new_step = Q_(value).to(base_units).m
                        except Exception as exc:
                            raise InstrumentManagerError(f'The value entered as the step [{value}] for feat [{feat_name}] couldn\'t be interpretted as a valid value with units [{base_units}]', exception=exc) from None
                        pyqt_widget.setOpts(step=new_step)
                elif isinstance(feat_value, int):
                    step_widget.setText('1')
                    def set_step_func(value):
                        try:
                            new_step = int(base_units)
                        except Exception as exc:
                            raise InstrumentManagerError(f'The value entered as the step [{value}] for feat [{feat_name}] couldn\'t be interpretted as a valid int', exception=exc) from None
                        pyqt_widget.setOpts(step=new_step)
                elif isinstance(feat_value, float):
                    step_widget.setText('1.0')
                    def set_step_func(value):
                        try:
                            new_step = float(base_units)
                        except Exception as exc:
                            raise InstrumentManagerError(f'The value entered as the step [{value}] for feat [{feat_name}] couldn\'t be interpretted as a valid float', exception=exc) from None
                        pyqt_widget.setOpts(step=new_step)
                else:
                    raise InstrumentManagerError('')
                # update the spinbox step size
                set_step_func(step_widget.text())
                step_widget.textChanged.connect(set_step_func)

                # wrap widgets in a horizontal layout and widget to format column because
                # a step_widget is being used to specify step size
                layout = QHBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(pyqt_widget)
                layout.addSpacing(29)
                layout.addWidget(step_label)
                layout.addWidget(step_widget)
                widget = QWidget()
                widget.setLayout(layout)

        # the lantz feat is a string, so we will just make a text box
        elif isinstance(feat_value, str):
            widget = QLineEdit()
            widget.setText(feat_value)
            def setattr_func(value):
                setattr(device, feat_name, widget.text())

            if read_only:
                widget.setReadOnly(True)
            else:
                widget.textChanged.connect(setattr_func)

            def getattr_func(value, old_value, widget=widget):
                widget.setText(value)
                widget_color = widget.palette().base().color().name()  # 'base: #191919'
                widget.setStyleSheet('background-color: {}'.format(UPDATE_HEX_COLOR))
                QTimer.singleShot(UPDATE_DISPLAY_TIME, lambda: widget.setStyleSheet('selection-background-color: {}'.format(widget_color)))

        # some unknown type - make a readonly text box containing str(feat)
        else:
            widget = QLineEdit()
            widget.setText(str(feat))
            widget.setReadOnly(True)
            def getattr_func(value, old_value, widget=widget):
                widget.setText(str(value))
                widget_color = widget.palette().base().color().name()  # 'base: #191919'
                widget.setStyleSheet('background-color: {}'.format(UPDATE_HEX_COLOR))
                QTimer.singleShot(UPDATE_DISPLAY_TIME, lambda: widget.setStyleSheet('selection-background-color: {}'.format(widget_color)))

        return widget, getattr_func

    def _generate_action_widget(self, device, action, action_name):
        """Generate a Qt gui element for a lantz action."""
        action_button = QPushButton(action_name, self.tree)
        action_button.setFont(QFont('Helvetica [Cronyx]', 12))
        def sizeHint(self):
            return ROW_QSIZE
        action_button.sizeHint = sizeHint.__get__(action_button, QPushButton)

        def action_func():
            getattr(device, action_name)()
        action_button.clicked.connect(action_func)

        return action_button


if __name__ == '__main__':
    import logging
    import sys
    from PyQt5.QtCore import Qt
    from nspyre.gui.app import NSpyreApp
    from nspyre.misc.logging import nspyre_init_logger

    nspyre_init_logger(logging.INFO)

    logger.info('starting Instrument Manager...')
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = NSpyreApp([sys.argv])
    pyqtgraph_connectCleanup()
    config_path = load_meta_config(CLIENT_META_CONFIG_PATH)
    with InservGateway(config_path) as isg:
        inserv_window = InstrumentManagerWindow(isg)
        app.exec()
    sys.exit()
