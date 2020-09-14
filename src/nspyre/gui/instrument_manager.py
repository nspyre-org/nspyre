#!/usr/bin/env python
"""
This instrument manager is a GUI which can connect to a set of
instrument servers and control the associated devices

Author: Alexandre Bourassa
Date: 10/30/2019
Modified: Jacob Feder 7/25/2020
"""

###########################
# imports
###########################

# std
import logging

# 3rd party
from PyQt5 import QtWidgets, QtCore
import sip

# nspyre
from nspyre.inserv.gateway import InservGateway
from nspyre.gui.widgets.feat import get_feat_widget
from nspyre.definitions import Q_, join_nspyre_path, MONGO_SERVERS_KEY
from nspyre.mongodb.mongo_listener import Synched_Mongo_Database

###########################
# exceptions
###########################

class InstrumentManagerWidgetError(Exception):
    """General InstrumentManagerWidget exception"""
    def __init__(self, msg):
        super().__init__(msg)

###########################
# classes
###########################

class Instrument_Manager_Widget(QtWidgets.QWidget):
    """ """
    def __init__(self, manager, parent=None):
        super().__init__(parent=parent)
        self.manager = manager

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(['Feat', 'value'])
        self.feat_items = dict()

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)
        self.setLayout(layout)

        # set some reasonable sizes
        s = QtWidgets.QApplication.desktop().screenGeometry()
        self.resize(s.width()//3,9*s.height()//10)
        # self.tree.resizeColumnToContents(0)
        # self.tree.resizeColumnToContents(1)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        self.tree.setColumnWidth(1, 1*s.width()//10)

        self.reset_all()
        self.synched_dbs = {}
        for s_name in self.manager.servers:
            # TODO dropdown for each server
            s_db_name = MONGO_SERVERS_KEY.format(s_name)
            self.synched_dbs[s_name] = Synched_Mongo_Database(
                                            MONGO_SERVERS_KEY.format(s_name),
                                            self.manager.mongo_addr)
            self.synched_dbs[s_name].updated_row.connect(self._update_feat_value)
            self.synched_dbs[s_name].col_dropped.connect(self.remove_instr)

    def _update_feat_value(self, dev_name, row):
        fname = row['name']
        if not dev_name in self.feat_items:
            self.update_instr(dev_name)
            return
        if row['type'] == 'feat':
            if (not row['value'] is None) and (not row['units'] is None):
                value = Q_(row['value'], row['units'])
            else:
                value = row['value']
            self.feat_items[dev_name][fname].set_requested.emit(value)
        elif row['type'] == 'dictfeat':
            value = row['value'].copy()
            for i, val in enumerate(row['value']):
                if (not row['value'][i] is None) and (not row['units'] is None):
                    value[i] = Q_(row['value'][i], row['units'])
            for key, w in self.feat_items[dev_name][fname].childs.items():
                self.feat_items[dev_name][fname].set_requested.emit(key, value)

    def reset_all(self):
        self.tree.clear()
        for dev_name in self.manager.devs:
            self.update_instr(dev_name)

    def update_instr(self, dev_specifier):
        # try: TODO
        self.tree.setSortingEnabled(False)

        # extract the server/device name from the device specifier
        # in the form 'server_name/dev_name'
        device = self.manager.devs[dev_specifier]
        server_name, dev_name = dev_specifier.split('/')
        instr_item = QtWidgets.QTreeWidgetItem(self.tree, [dev_name, ''])
        # mongodb collection containing the device attributes
        dev_collection = self.manager.mongo_client[MONGO_SERVERS_KEY.format(server_name)][dev_name]
        self.feat_items[dev_name] = {}
        for attribute in dev_collection.find():
            if attribute['type'] == 'dictfeat':
                feat_item = DictFeatTreeWidgetItem(attribute, self.tree, device)
                instr_item.addChild(feat_item.item)
            elif attribute['type'] == 'feat':
                feat_item = FeatTreeWidgetItem(attribute, self.tree, device)
                instr_item.addChild(feat_item.item)
                self.tree.setItemWidget(feat_item.item, 1, feat_item.w)
            elif attribute['type'] == 'action':
                feat_item = ActionTreeWidgetItem(attribute, self.tree, device)
                instr_item.addChild(feat_item.item)
                self.tree.setItemWidget(feat_item.item, 1, feat_item.w)
            self.feat_items[dev_name][attribute['name']] = feat_item
            self.tree.setItemWidget(feat_item.item, 0, QtWidgets.QLabel(attribute['name']))
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, QtCore.Qt.AscendingOrder)
        # except:
        #     print("Could not load {}".format(dev_name))
        #     self.remove_instr(dev_name)

    def remove_instr(self, dev_name):
        if dev_name in self.feat_items:
            self.feat_items.pop(dev_name)
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            c = root.child(i)
            if c.text(0) == dev_name:
                print('Removing device {}'.format(dev_name))
                root.removeChild(c)
                sip.delete(c)
                c = None
                break
        return

class FeatTreeWidgetItem(QtCore.QObject):
    # This signal will be triggered externally when the display value needs
    # to be changed (argument is value)
    set_requested = QtCore.pyqtSignal(object)
    # This signal will be triggered when the "go button" is clicked
    go_clicked = QtCore.pyqtSignal()
    # This signal will be triggered when the "read button" is clicked
    read_clicked = QtCore.pyqtSignal()
    def __init__(self, feat, parent_tree, dev):
        super().__init__()
        self.dev = dev
        self.feat = feat
        self.item = QtWidgets.QTreeWidgetItem(1)
        self.w = get_feat_widget(feat)

        self.set_requested.connect(self.w.set_requested)
        self.w.go_clicked.connect(self.set_dev)
        self.w.read_clicked.connect(self.get_dev)

    def set_dev(self):
        setattr(self.dev, self.feat['name'], self.w.getter())

    def get_dev(self):
        val = getattr(self.dev, self.feat['name'])
        self.set_requested.emit(val)

class DictFeatTreeWidgetItem(QtCore.QObject):
    set_requested = QtCore.pyqtSignal(object, object) # This signal will be triggered externally when the display value needs to be changed (arguments are <key, new value>)
    go_clicked = QtCore.pyqtSignal(object) # This signal will be triggered when the "go button" is clicked (argument is key)
    read_clicked = QtCore.pyqtSignal(object)  # This signal will be triggered when the "read button" is clicked (argument is key)

    def __init__(self, feat, parent_tree, dev):
        super().__init__()
        self.dev = dev
        self.feat = feat
        self.item = QtWidgets.QTreeWidgetItem(1)
        self.childs = {}
        temp_feat = feat.copy()
        for i,key in enumerate(feat['keys']):
            #assert isinstance(key, Hashable) TODO
            temp_feat['value'] = feat['value'][i]
            w = get_feat_widget(temp_feat)
            item = QtWidgets.QTreeWidgetItem(1)
            self.item.addChild(item)
            parent_tree.setItemWidget(item, 0, QtWidgets.QLabel(str(key)))
            parent_tree.setItemWidget(item, 1, w)
            self.childs[key] = w

            fgen = lambda _key: (lambda: self.go_clicked.emit(_key))
            w.go_clicked.connect(fgen(key))
            
            fgen = lambda _key: (lambda: self.read_clicked.emit(_key))
            w.read_clicked.connect(fgen(key))

        self.go_clicked.connect(self.set_dev)
        self.read_clicked.connect(self.get_dev)
        self.set_requested.connect(self.issue_set_requested)

    def issue_set_requested(self, key, val):
        i = list(self.childs.keys()).index(key)
        self.childs[key].set_requested.emit(val[i])

    def set_dev(self, key):
        # print('set_dev', self.dev, self.feat['name'], key, self.childs[key].getter())
        getattr(self.dev, self.feat['name'])[key] = self.childs[key].getter()

    def get_dev(self, key):
        # print('get_dev', self.dev, self.feat['name'], key, self.childs[key].getter())
        val = getattr(self.dev, self.feat['name'])[key]
        self.childs[key].set_requested.emit(val)

class ActionTreeWidgetItem(QtCore.QObject):
    clicked = QtCore.pyqtSignal()

    def __init__(self, action, parent_tree, dev):
        super().__init__()
        self.dev = dev
        self.action = action
        self.item = QtWidgets.QTreeWidgetItem(1)
        self.w = QtWidgets.QPushButton(self.action['name'])

        self.w.clicked.connect(self.run_action)
        self.w.clicked.connect(self.clicked)

    def run_action(self):
        getattr(self.dev, self.action['name'])()

if __name__ ==  '__main__':
    from nspyre.gui.app import NSpyreApp

    # configure server logging behavior
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s -- %(levelname)s -- %(message)s',
                        handlers=[logging.StreamHandler()])
    app = NSpyreApp([])
    with InservGateway() as im:
        w = Instrument_Manager_Widget(im)
        w.show()
        app.exec_()
