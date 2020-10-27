#!/usr/bin/env python
"""
This instrument manager is a GUI which can connect to a set of
instrument servers and control the associated devices

Author: Michael Solomon, Jacob Feder
Date: 10/26/2020
"""

###########################
# imports
###########################

import functools
from pathlib import Path

from PyQt5.QtCore import QProcess, QSize
from PyQt5.QtGui import QFont
from pyqtgraph import SpinBox
from PyQt5.QtWidgets import QComboBox, QMainWindow, QPushButton, QTreeWidget, \
                            QTreeWidgetItem, QVBoxLayout, QWidget, QHeaderView, \
                            QApplication, QLineEdit

# nspyre
from nspyre.inserv.gateway import InservGateway
from nspyre.gui.widgets.feat import get_feat_widget
from nspyre.definitions import Q_, join_nspyre_path, MONGO_SERVERS_KEY
from nspyre.mongodb.mongo_listener import Synched_Mongo_Database

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
    """This is progress, I promise."""
    def __init__(self, gateway, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('NSpyre Instrument Manager')

        # Set the main window layout to consist of vertical boxes.
        # The QVBoxLayout class lines up widgets vertically.
        layout = QVBoxLayout()

        # connection to the instrument servers
        self.gateway = gateway
        # tree of dictionaries that contains all of the instrument
        # manager GUI elements
        # the top level of the dictionary is the instrument servers
        # the next level is the devices
        # the bottom level is attributes of the devices
        # e.g.               ----------self.gui----------
        #                   /                            \
        #               server1                        server2
        #              /       \                      /       \
        #      sig-gen1         scope1        sig-gen2         laser
        #      /      \        /      \      /        \       /     \
        #   freq     ampl    trig    din[] freq      ampl  lambda  power
        # self.gui = {}

        # set main GUI layout
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(['Lantz Feat', 'value'])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)
        self.setLayout(layout)

        # set some reasonable sizes
        s = QApplication.desktop().screenGeometry()
        # self.resize(s.width()//3,9*s.height()//10)

        # self.tree.header().setStretchLastSection(False)
        # self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        # self.tree.header().setSectionResizeMode(1, QHeaderView.Interactive)
        # self.tree.setColumnWidth(1, 1*s.width()//10)
        self._create_widgets()
        # self.tree.setUniformRowHeights(True)
        self.tree.indexRowSizeHint(4)
        self.tree.show()

    def _create_widgets(self):
        """Iterate over the available servers and devices, and collect their
        attributes that can be modified by the instrument manager GUI, then
        populate the self.gui and update the GUI"""
        for server_name, server in self.gateway.servers.items():
            server_tree = QTreeWidgetItem(self.tree, [server_name, ''])
            server_tree.setExpanded(True)
            for device_name, device in server.root._devs.items():
                device_tree = QTreeWidgetItem(server_tree, [device_name, ''])
                for feat_name, feat in device._lantz_feats.items():
                    w = self._generate_feat_widget(feat, feat_name, device)
                    feat_tree = QTreeWidgetItem(device_tree, [feat_name, ''])
                    # feat_tree.setSizeHint(1, QSize(-1, 15))
                    self.tree.setItemWidget(feat_tree, 1, w)
                # for dictfeat_name, dictfeat in device._lantz_dictfeats.items():
                #     self.generate_dictfeat_widget(dictfeat, dictfeat_name, device, device_tree)

                # for action_name, action in device._lantz_actions.items():
                #     self.generate_action_widget(action, action_name, device, device_tree)

    def _generate_feat_widget(self, feat, feat_name, device):
        """Generate a Qt gui element for a lantz feat"""
        val = getattr(device, feat_name)
        if feat._config['values']:
            # the lantz feat has only a specific set of allowed values
            # so we make a dropdown box
            widget = QComboBox()
            str_vals = [str(s) for s in list(feat._config['values'].keys())]
            widget.addItems(str_vals)
            widget.setCurrentIndex(0)
            setattr_func = lambda value, feat=feat: setattr(feat, widget.currentText())
            widget.activated.connect(setattr_func)
            getattr_func = lambda value, old_value: widget.setCurrentText(value)
        elif isinstance(val, (int, float, Q_)) or feat._config['units']:
            optional_args = {}
            if feat._config['units'] is not None:
                optional_args['unit'] = feat._config['units']
            if feat._config['limits'] is not None:
                optional_args['bounds'] = feat._config['limits']
            optional_args['dec'] = True
            optional_args['minStep'] = 1e-3
            optional_args['decimals'] = 10
            if isinstance(val, int):
                optional_args['int'] = True
                optional_args['minStep'] = 1
                optional_args['decimals'] = 10
            widget = SpinBox()
            setattr_func = lambda value: print(value)
            # TODO
            getattr_func = lambda value, old_value: print(value)
            widget.sigValueChanged.connect(setattr_func)
            #widget.valueChanged.connect(functools.partial(lambda idx: feat = widget.setValue()))
            #widget.sp.valueChanged.connect(self.valuechange)
        else:
            widget = QLineEdit()
            getattr_func = lambda value, old_value: print(value)
            widget.setText('test')
            widget.setReadOnly(feat._config['read_once'])
        # elif getattr(device, feat_name) is None:
        #     w = LineEditFeatWidget(text = 'Unknown type')
        #     w.set_readonly(True)
        #     return w
        # else:
        #     w = LineEditFeatWidget(text = getattr(device, feat_name)) 

        # widget.set_readonly(feat._config['read_once'])
        # if (not feat['value'] is None) and (not feat['units'] is None):
        #     w.setter(Q_(feat['value'], feat['units']))
        # else:
        #     w.setter(feat['value'])

        getattr(device, feat_name + '_changed').connect(getattr_func)
        return widget






        # device = self.manager.devs[dev_specifier]
        # server_name, dev_name = dev_specifier.split('/')
        # instr_item = QtWidgets.QTreeWidgetItem(self.tree, [dev_name, ''])
        # # mongodb collection containing the device attributes
        # dev_collection = self.manager.mongo_client[MONGO_SERVERS_KEY.format(server_name)][dev_name]
        # self.feat_items[dev_name] = {}
        # for attribute in dev_collection.find():
        #     if attribute['type'] == 'dictfeat':
        #         feat_item = DictFeatTreeWidgetItem(attribute, self.tree, device)
        #         instr_item.addChild(feat_item.item)
        #     elif attribute['type'] == 'feat':
        #         feat_item = FeatTreeWidgetItem(attribute, self.tree, device)
        #         instr_item.addChild(feat_item.item)
        #         self.tree.setItemWidget(feat_item.item, 1, feat_item.w)
        #     elif attribute['type'] == 'action':
        #         feat_item = ActionTreeWidgetItem(attribute, self.tree, device)
        #         instr_item.addChild(feat_item.item)
        #         self.tree.setItemWidget(feat_item.item, 1, feat_item.w)
        #     self.feat_items[dev_name][attribute['name']] = feat_item
        #     self.tree.setItemWidget(feat_item.item, 0, QtWidgets.QLabel(attribute['name']))
        # self.tree.setSortingEnabled(True)
        # self.tree.sortByColumn(0, QtCore.Qt.AscendingOrder)


        # parent_tree.setItemWidget(item, 0, QtWidgets.QLabel(str(key)))
        # parent_tree.setItemWidget(item, 1, w)


        # self.reset_all()
        # self.synched_dbs = {}
        # for s_name in self.manager.servers:
        #     # TODO dropdown for each server
        #     s_db_name = MONGO_SERVERS_KEY.format(s_name)
        #     self.synched_dbs[s_name] = Synched_Mongo_Database(
        #                                     MONGO_SERVERS_KEY.format(s_name),
        #                                     self.manager.mongo_addr)
        #     self.synched_dbs[s_name].updated_row.connect(self._update_feat_value)
        #     self.synched_dbs[s_name].col_dropped.connect(self.remove_instr)
        # self.show()


# class FeatTreeWidgetItem(QtCore.QObject):
#     # This signal will be triggered externally when the display value needs
#     # to be changed (argument is value)
#     set_requested = QtCore.pyqtSignal(object)
#     # This signal will be triggered when the "go button" is clicked
#     go_clicked = QtCore.pyqtSignal()
#     # This signal will be triggered when the "read button" is clicked
#     read_clicked = QtCore.pyqtSignal()
#     def __init__(self, feat, parent_tree, dev):
#         super().__init__()
#         self.dev = dev
#         self.feat = feat
#         self.item = QtWidgets.QTreeWidgetItem(1)
#         self.w = get_feat_widget(feat)

#         self.set_requested.connect(self.w.set_requested)
#         self.w.go_clicked.connect(self.set_dev)
#         self.w.read_clicked.connect(self.get_dev)

#     def set_dev(self):
#         setattr(self.dev, self.feat['name'], self.w.getter())

#     def get_dev(self):
#         val = getattr(self.dev, self.feat['name'])
#         self.set_requested.emit(val)











#     def _update_feat_value(self, dev_name, row):
#         fname = row['name']
#         if not dev_name in self.feat_items:
#             self.update_instr(dev_name)
#             return
#         if row['type'] == 'feat':
#             if (not row['value'] is None) and (not row['units'] is None):
#                 value = Q_(row['value'], row['units'])
#             else:
#                 value = row['value']
#             self.feat_items[dev_name][fname].set_requested.emit(value)
#         elif row['type'] == 'dictfeat':
#             value = row['value'].copy()
#             for i, val in enumerate(row['value']):
#                 if (not row['value'][i] is None) and (not row['units'] is None):
#                     value[i] = Q_(row['value'][i], row['units'])
#             for key, w in self.feat_items[dev_name][fname].childs.items():
#                 self.feat_items[dev_name][fname].set_requested.emit(key, value)

#     def reset_all(self):
#         self.tree.clear()
#         for dev_name in self.manager.devs:
#             self.update_instr(dev_name)

#     def update_instr(self, dev_specifier):
#         # try: TODO
#         self.tree.setSortingEnabled(False)

#         # extract the server/device name from the device specifier
#         # in the form 'server_name/dev_name'
#         device = self.manager.devs[dev_specifier]
#         server_name, dev_name = dev_specifier.split('/')
#         instr_item = QtWidgets.QTreeWidgetItem(self.tree, [dev_name, ''])
#         # mongodb collection containing the device attributes
#         dev_collection = self.manager.mongo_client[MONGO_SERVERS_KEY.format(server_name)][dev_name]
#         self.feat_items[dev_name] = {}
#         for attribute in dev_collection.find():
#             if attribute['type'] == 'dictfeat':
#                 feat_item = DictFeatTreeWidgetItem(attribute, self.tree, device)
#                 instr_item.addChild(feat_item.item)
#             elif attribute['type'] == 'feat':
#                 feat_item = FeatTreeWidgetItem(attribute, self.tree, device)
#                 instr_item.addChild(feat_item.item)
#                 self.tree.setItemWidget(feat_item.item, 1, feat_item.w)
#             elif attribute['type'] == 'action':
#                 feat_item = ActionTreeWidgetItem(attribute, self.tree, device)
#                 instr_item.addChild(feat_item.item)
#                 self.tree.setItemWidget(feat_item.item, 1, feat_item.w)
#             self.feat_items[dev_name][attribute['name']] = feat_item
#             self.tree.setItemWidget(feat_item.item, 0, QtWidgets.QLabel(attribute['name']))
#         self.tree.setSortingEnabled(True)
#         self.tree.sortByColumn(0, QtCore.Qt.AscendingOrder)
#         # except:
#         #     print("Could not load {}".format(dev_name))
#         #     self.remove_instr(dev_name)

#     def remove_instr(self, dev_name):
#         if dev_name in self.feat_items:
#             self.feat_items.pop(dev_name)
#         root = self.tree.invisibleRootItem()
#         for i in range(root.childCount()):
#             c = root.child(i)
#             if c.text(0) == dev_name:
#                 print('Removing device {}'.format(dev_name))
#                 root.removeChild(c)
#                 sip.delete(c)
#                 c = None
#                 break
#         return

# class FeatTreeWidgetItem(QtCore.QObject):
#     # This signal will be triggered externally when the display value needs
#     # to be changed (argument is value)
#     set_requested = QtCore.pyqtSignal(object)
#     # This signal will be triggered when the "go button" is clicked
#     go_clicked = QtCore.pyqtSignal()
#     # This signal will be triggered when the "read button" is clicked
#     read_clicked = QtCore.pyqtSignal()
#     def __init__(self, feat, parent_tree, dev):
#         super().__init__()
#         self.dev = dev
#         self.feat = feat
#         self.item = QtWidgets.QTreeWidgetItem(1)
#         self.w = get_feat_widget(feat)

#         self.set_requested.connect(self.w.set_requested)
#         self.w.go_clicked.connect(self.set_dev)
#         self.w.read_clicked.connect(self.get_dev)

#     def set_dev(self):
#         setattr(self.dev, self.feat['name'], self.w.getter())

#     def get_dev(self):
#         val = getattr(self.dev, self.feat['name'])
#         self.set_requested.emit(val)

# class DictFeatTreeWidgetItem(QtCore.QObject):
#     set_requested = QtCore.pyqtSignal(object, object) # This signal will be triggered externally when the display value needs to be changed (arguments are <key, new value>)
#     go_clicked = QtCore.pyqtSignal(object) # This signal will be triggered when the "go button" is clicked (argument is key)
#     read_clicked = QtCore.pyqtSignal(object)  # This signal will be triggered when the "read button" is clicked (argument is key)

#     def __init__(self, feat, parent_tree, dev):
#         super().__init__()
#         self.dev = dev
#         self.feat = feat
#         self.item = QtWidgets.QTreeWidgetItem(1)
#         self.childs = {}
#         temp_feat = feat.copy()
#         for i,key in enumerate(feat['keys']):
#             #assert isinstance(key, Hashable) TODO
#             temp_feat['value'] = feat['value'][i]
#             w = get_feat_widget(temp_feat)
#             item = QtWidgets.QTreeWidgetItem(1)
#             self.item.addChild(item)
#             parent_tree.setItemWidget(item, 0, QtWidgets.QLabel(str(key)))
#             parent_tree.setItemWidget(item, 1, w)
#             self.childs[key] = w

#             fgen = lambda _key: (lambda: self.go_clicked.emit(_key))
#             w.go_clicked.connect(fgen(key))
            
#             fgen = lambda _key: (lambda: self.read_clicked.emit(_key))
#             w.read_clicked.connect(fgen(key))

#         self.go_clicked.connect(self.set_dev)
#         self.read_clicked.connect(self.get_dev)
#         self.set_requested.connect(self.issue_set_requested)

#     def issue_set_requested(self, key, val):
#         i = list(self.childs.keys()).index(key)
#         self.childs[key].set_requested.emit(val[i])

#     def set_dev(self, key):
#         # print('set_dev', self.dev, self.feat['name'], key, self.childs[key].getter())
#         getattr(self.dev, self.feat['name'])[key] = self.childs[key].getter()

#     def get_dev(self, key):
#         # print('get_dev', self.dev, self.feat['name'], key, self.childs[key].getter())
#         val = getattr(self.dev, self.feat['name'])[key]
#         self.childs[key].set_requested.emit(val)

# class ActionTreeWidgetItem(QtCore.QObject):
#     clicked = QtCore.pyqtSignal()

#     def __init__(self, action, parent_tree, dev):
#         super().__init__()
#         self.dev = dev
#         self.action = action
#         self.item = QtWidgets.QTreeWidgetItem(1)
#         self.w = QtWidgets.QPushButton(self.action['name'])

#         self.w.clicked.connect(self.run_action)
#         self.w.clicked.connect(self.clicked)

#     def run_action(self):
#         getattr(self.dev, self.action['name'])()

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
    with InservGateway() as isg:
        print('I made it!')
        inserv_window = InstrumentManagerWindow(isg)
        print('this is odd')
        app.exec()


# {'_MessageBasedDriver__resource_manager': <ResourceManager(<VisaLibrary('unset')>)>,
#  '_Base__name': 'LantzSignalGenerator0',
#  'logger_name': 'lantz.driver.LantzSignalGenerator0',
#  '_Base__keep_alive': [],
#  '_StorageMixin__storage': {'iconfig': defaultdict(<class 'dict'>, {'idn': {}, 'amplitude': {}, 'offset': {}, 'frequency': {}, 'output_enabled': {}, 'waveform': {}, 'dout': {}, DictPropertyNameKey(name='dout', key=1): {}}),
#                             'iconfigm': defaultdict(<class 'dict'>, {'initialize': {}}),
#                             'statsm': defaultdict(<class 'pimpmyclass.stats.RunningStats'>, {'initialize': {'call': <pimpmyclass.stats.RunningState object at 0x7f9b2b382250>}}),
#                             'stats': defaultdict(<class 'pimpmyclass.stats.RunningStats'>, {'amplitude': {'get': <pimpmyclass.stats.RunningState object at 0x7f9b2b4d0a90>}, 'frequency': {'get': <pimpmyclass.stats.RunningState object at 0x7f9b2b4d0e50>}, DictPropertyNameKey(name='dout', key=1): {'get': <pimpmyclass.stats.RunningState object at 0x7f9b2b4e4280>}}),
#                             'cache': {'amplitude': <Quantity(0.0, 'volt')>, 'frequency': <Quantity(1000.0, 'hertz')>, DictPropertyNameKey(name='dout', key=1): False}
#                             },
#  '_lantz_anyfeat': ChainMap({'idn': <lantz.core.feat.Feat object at 0x7f9b2b382bb0>, 'amplitude': <lantz.core.feat.Feat object at 0x7f9b2b382af0>, 'offset': <lantz.core.feat.Feat object at 0x7f9b2b382b80>, 'frequency': <lantz.core.feat.Feat object at 0x7f9b2b382fd0>, 'output_enabled': <lantz.core.feat.Feat object at 0x7f9b2b2527f0>, 'waveform': <lantz.core.feat.Feat object at 0x7f9b2b382c10>, DictPropertyNameKey(name='dout', key=1): <lantz.core.feat.Feat object at 0x7f9b2b4d0580>}, {'dout': <lantz.core.feat.DictFeat object at 0x7f9b2b382e80>, 'din': <lantz.core.feat.DictFeat object at 0x7f9b2b382cd0>}),
#  '_LogMixin__logger': <Logger lantz.driver.LantzSignalGenerator0 (DEBUG)>,
#  'DEFAULTS': mappingproxy({'COMMON': {'write_termination': '\n', 'read_termination': '\n'}}),
#  'resource_name': 'TCPIP::localhost::5678::SOCKET',
#  'resource_kwargs': {'write_termination': '\n', 'read_termination': '\n'},
#  'resource': <'TCPIPSocket'('TCPIP::localhost::5678::SOCKET')>,
#  '_LockMixin__async_lock': <unlocked _thread.RLock object owner=0 count=0 at 0x7f9b2b492e10>}

