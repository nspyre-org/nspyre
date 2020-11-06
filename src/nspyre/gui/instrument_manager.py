#!/usr/bin/env python
"""
This instrument manager is a GUI which can connect to a set of
instrument servers and control the associated devices

Author: Michael Solomon, Jacob Feder
Date: 10/26/2020
"""

# std
import functools

# 3rd party
from PyQt5.QtCore import Qt, QProcess, QSize
from PyQt5.QtGui import QFont
from pyqtgraph import SpinBox
from pyqtgraph import exit as pyqtgraph_exit
from pyqtgraph import _connectCleanup as pyqtgraph_connectCleanup
from PyQt5.QtWidgets import QApplication, QComboBox, QLineEdit, QMainWindow, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHeaderView

# nspyre
from nspyre.inserv.gateway import InservGateway
from nspyre.definitions import Q_

###########################
# exceptions
###########################

class InstrumentManagerError(Exception):
    """General InstrumentManagerWidget exception"""
    def __init__(self, msg):
        super().__init__(msg)

###########################
# classes
###########################

class InstrumentManagerWindow(QMainWindow):
    """Creates a GUI interface for controlling instrument attributes
    based on a dropdown / tree structure
    the top level is the instrument servers
    the next level is the devices
    the bottom level is attributes of the devices"""

    def __init__(self, gateway, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('NSpyre Instrument Manager')

        # connection to the instrument servers
        self.gateway = gateway
        self._slots = []

        # set main GUI layout
        self.tree = QTreeWidget()
        self.tree.setFont(QFont('Helvetica [Cronyx]', 14))
        self.tree.setColumnCount(2)
        self.tree.setMinimumHeight(self.tree.height())

        # configure the QTreeWidget Header
        header = self.tree.header()
        header.setHidden(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionsMovable(True)
        header.setStretchLastSection(False)

        # generate GUI elements
        self._create_widgets()

        self.setCentralWidget(self.tree)
        self.tree.expandAll()
        # Adding 2pt of padding to the margin to remove horizontal scroll bar and 14pt of padding for the vertical scroll bar
        self.tree.setMinimumWidth(self.tree.columnWidth(0) + self.tree.columnWidth(1) + 2 + 14)
        self.tree.collapseAll()
        # start GUI with the servers expanded
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setExpanded(True)
        self.show()

    def _create_widgets(self):
        """Iterate over the available servers and devices, collect their
        attributes that can be modified by the instrument manager GUI, then
        populate the self.gui"""

        # iterate over servers
        for server_name, server in self.gateway.servers().items():
            server_tree = QTreeWidgetItem(self.tree, [server_name, ''])
            server_tree.setExpanded(True)

            # iterate over devices
            for device_name, device in server.root._devs.items():
                device_tree = QTreeWidgetItem(server_tree, [device_name, ''])
                device_tree.setExpanded(True)

                # handle feats
                for feat_name, feat in device._lantz_feats.items():
                    feat_widget, feat_getattr = self._generate_feat_widget(feat, feat_name, device)        
                    # we have to use a partial here because PySignal and RPyC don't
                    # play nicely if you .connect() a lambda or other function / method
                    # to PySignal
                    getattr_partial = functools.partial(feat_getattr)
                    # register the feat_getattr() to be called when the feat changes using
                    # pimpmyclass "ObservableProperty" mixin
                    getattr(device, feat_name + '_changed').connect(getattr_partial)
                    
                    feat_widget.setFont(QFont('Helvetica [Cronyx]', 14))
                    feat_item = QTreeWidgetItem(device_tree, [feat_name, ''])
                    feat_item.sizeHint(0)
                    feat_item.setSizeHint(1, QSize(79,24))
                    self.tree.setItemWidget(feat_item, 1, feat_widget)

                # handle dictfeats
                for dictfeat_name, dictfeat in device._lantz_dictfeats.items():
                    dictfeat_tree = QTreeWidgetItem(device_tree, [dictfeat_name, ''])

                    for feat_key in dictfeat.keys:
                        feat = dictfeat.subproperty(getattr(device, dictfeat_name).instance, feat_key)
                        feat_widget, feat_getattr = self._generate_feat_widget(feat, dictfeat_name, device, dictfeat_key=feat_key)
                        feat_item = QTreeWidgetItem(dictfeat_tree, ['{} {}'.format(dictfeat_name, feat_key), ''])
                        self.tree.setItemWidget(feat_item, 1, feat_widget)
                        if feat_key == dictfeat.keys[-1]:
                            # connect the feat_getattr() to be called when the feat changes using
                            # pimpmyclass "ObservableProperty" mixin
                            def dictfeat_getattr(df_tree, getattr_func, df_keys, value, old_value, key):
                                w = self.tree.itemWidget(df_tree.child(df_keys.index(key)), 1)
                                getattr_func(value, old_value, widget=w)
                            # we have to use a partial here because PySignal and RPyC don't
                            # play nicely if you .connect() a lambda or other function / method
                            # to PySignal
                            # TODO
                            #from PyQt5.QtCore import pyqtRemoveInputHook; pyqtRemoveInputHook()
                            #import pdb; pdb.set_trace()
                            getattr_partial = functools.partial(dictfeat_getattr, dictfeat_tree, feat_getattr, dictfeat.keys)
                            getattr(device, dictfeat_name + '_changed').connect(getattr_partial)

                # handle actions
                action_tree = QTreeWidgetItem(device_tree, ['Actions', ''])
                for action_name, action in device._lantz_actions.items():
                    # actions that shouldn't be added to the GUI
                    ignore_actions = ['initialize', 'finalize', 'update', 'refresh']
                    if action_name in ignore_actions or '_async' in action_name:
                        continue

                    action_widget = self._generate_action_widget(device, action, action_name)
                    action_widget.setFont(QFont('Helvetica [Cronyx]', 14))
                    action_item = QTreeWidgetItem(action_tree, [action_name, ''])
                    self.tree.setItemWidget(action_item, 1, action_widget)

    def _generate_feat_widget(self, feat, feat_name, device, dictfeat_key=None):
        """Generate a Qt gui element for a lantz feat"""

        if dictfeat_key:
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
                def getattr_func_lineedit(value, old_value, widget=widget):
                    widget.setText(value)
                getattr_func = getattr_func_lineedit
            else:
                widget = QComboBox()
                # dictionary mapping the possible lantz values to str(values)
                # e.g. {'True' : True, 'False' : False}
                keymapping_dict = {}
                for k in feat._config['values'].keys():
                    keymapping_dict[str(k)] = k
                
                # add the possible values to the dropdown list
                widget.addItems(keymapping_dict.keys())
                widget.setCurrentIndex(list(keymapping_dict.values()).index(feat_value))
                
                # callback function for when the user changes the dropdown selection
                def setattr_func_combobox(value, key=None):
                    if key:
                        getattr(device, feat_name)[key] = keymapping_dict[widget.currentText()]
                    else:
                        setattr(device, feat_name, keymapping_dict[widget.currentText()])
                setattr_partial_combobox = functools.partial(setattr_func_combobox, key=dictfeat_key)
                # call setattr_func() when the combo box value is set from the GUI
                widget.activated.connect(setattr_partial_combobox)

                # callback function to modify the GUI when the the feat is changed externally
                def getattr_func_combobox(value, old_value, widget=widget):
                    # because the _changed is shared for all keys of the same dictfeat,
                    # we have to check to see if this was the key that was actually changed
                    widget.setCurrentIndex(list(keymapping_dict.values()).index(value))
                getattr_func = getattr_func_combobox

        # the lantz feat is some sort of numerical value, so we will
        # generate a SpinBox (number entry with increment / decrement arrow keys)
        elif isinstance(feat_value, (int, float, Q_)):
            # arguments for the SpinBox
            optional_args = {}
            
            if feat._config['units']:
                optional_args['suffix'] = feat._config['units']
            
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

            # stepping strategy
            optional_args['dec'] = False
            optional_args['minStep'] = 1e-6
            # number of decimal places to display
            optional_args['decimals'] = 6
            optional_args['compactHeight'] = False
            if isinstance(feat_value, int):
                optional_args['int'] = True
                optional_args['minStep'] = 1
                # optional_args['decimals'] = 10
            
            widget = SpinBox(**optional_args)

            widget.resize(79, 24)
            def sizeHint(self):
                return QSize(79, 24)
            widget.sizeHint = sizeHint.__get__(widget, SpinBox)

            if isinstance(feat_value, Q_):
                widget.setValue(feat_value.to(feat._config['units']).m)
            else:
                widget.setValue(feat_value)
            
            if feat._config['units']:
                # callback function for when the user changes the value from the GUI
                def setattr_func_spinbox(value):
                    setattr(device, feat_name, Q_(widget.value(), feat._config['units']))
                # callback function to modify the GUI when the the feat is changed externally
                def getattr_func_spinbox(value, old_value, widget=widget):
                    if isinstance(value, Q_):
                        widget.setValue(value.to(feat._config['units']).m)
                    else:
                        widget.setValue(value)
            else:
                def setattr_func_spinbox(value):
                    setattr(device, feat_name, widget.value())
                def getattr_func_spinbox(value, old_value, widget=widget):
                    widget.setValue(value)
            getattr_func = getattr_func_spinbox
            
            if read_only:
                widget.lineEdit().setReadOnly(True)
            else:
                widget.sigValueChanged.connect(setattr_func_spinbox)

        # the lantz feat is a string, so we will just make a text box
        elif isinstance(feat_value, str):
            widget = QLineEdit()
            widget.setText(feat_value)
            def setattr_func_lineedit(value):
                setattr(device, feat_name, widget.text())

            if read_only:
                widget.setReadOnly(True)
            else:
                widget.textChanged.connect(setattr_func_lineedit)

            def getattr_func_lineedit(value, old_value, widget=widget):
                widget.setText(value)
            getattr_func = getattr_func_lineedit

        # some unknown type - make a readonly text box containing str(feat)
        else:
            widget = QLineEdit()
            widget.setText(str(feat))
            widget.setReadOnly(True)
            def getattr_func_lineedit_ro(value, old_value, widget=widget):
                widget.setText(value)
            getattr_func = getattr_func_lineedit_ro

        return (widget, getattr_func)

    def _generate_action_widget(self, device, action, action_name):
        """Generate a Qt gui element for a lantz action"""
        action_button = QPushButton(action_name, self.tree)
        action_button.setFont(QFont('Helvetica [Cronyx]', 12))

        def action_func():
            getattr(device, action_name)()
        action_button.clicked.connect(action_func)

        return action_button

if __name__ ==  '__main__':
    import logging
    import sys
    from PyQt5.QtCore import Qt
    from nspyre.gui.app import NSpyreApp

    # configure server logging behavior
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s -- %(levelname)s -- %(message)s',
                        handlers=[logging.StreamHandler()])

    logging.info('starting Instrument Manager...')

    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = NSpyreApp([sys.argv])

    # TODO
    #pyqtgraph_connectCleanup()

    with InservGateway() as isg:
        inserv_window = InstrumentManagerWindow(isg)
        app.exec()
