"""
    spyre.widgets.instrument_manager.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This instrument manager is a Widget which can connect to an Instrument server and control the associated devices

    Author: Alexandre Bourassa
    Date: 10/30/2019
"""

from importlib import import_module
from collections import OrderedDict

import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore
import sip

from nspyre.instrument_server import Instrument_Server_Client, load_remote_device
from nspyre.instrument_manager import Instrument_Manager
from feat import get_feat_widget

from lantz import Q_

class Instrument_Manager_Widget(QtWidgets.QWidget):

    def __init__(self, manager, parent=None):
        if not manager.fully_mongo:
            raise Exception("Instrument_Manager_Widget requires an Instrument Manager which is fully mongo")
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

        #Set some resonable sizes
        s = QtWidgets.QApplication.desktop().screenGeometry()
        self.resize(s.width()//3,9*s.height()//10)
        # self.tree.resizeColumnToContents(0)
        # self.tree.resizeColumnToContents(1)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        # 
        self.tree.setColumnWidth(1, 1*s.width()//10)

        self.reset_all()

        self.manager.launch_watchers()
        for c in self.manager.clients:
            c['watcher'].updated_row.connect(self._update_feat_value)
            c['watcher'].col_dropped.connect(self.remove_instr)

    def _update_feat_value(self, dname, row):
        fname = row['name']
        if not dname in self.feat_items:
            self.update_instr(dname)
            return
        # print(row)
        # print(row['type'])
        if row['type'] == 'feat':
            self.feat_items[dname][fname].set_requested.emit(row['value'])
        elif row['type'] == 'dictfeat':
            for key, w in self.feat_items[dname][fname].childs.items():
                self.feat_items[dname][fname].set_requested.emit(key, row['value'])

    
    def reset_all(self):
        self.tree.clear()
        for dname in self.manager.instr:
            self.update_instr(dname)

    def update_instr(self, dname):
        self.tree.setSortingEnabled(False)

        dclass = self.manager.get(dname)['class']
        class_name = dclass.split('.')[-1]
        mod = import_module(dclass.replace('.'+class_name, ''))
        c = getattr(mod, class_name)

        self.manager.get(dname)['zmq'].get_none_feat(dname)
    
        instr_item = QtWidgets.QTreeWidgetItem(self.tree, [dname, ''])
        feats = self.manager.get(dname)['mongo'].find({},{'_id':False})
        
        self.feat_items[dname] = dict()
        for feat in feats:
            if feat['type'] == 'dictfeat':
                feat_item = DictFeatTreeWidgetItem(feat, self.tree, self.manager.get(dname)['dev'])
                instr_item.addChild(feat_item.item)
            elif feat['type'] == 'feat':
                feat_item = FeatTreeWidgetItem(feat, self.tree, self.manager.get(dname)['dev'])
                instr_item.addChild(feat_item.item)
                self.tree.setItemWidget(feat_item.item, 1, feat_item.w)
            elif feat['type'] == 'action':
                feat_item = ActionTreeWidgetItem(feat, self.tree, self.manager.get(dname)['dev'])
                instr_item.addChild(feat_item.item)
                self.tree.setItemWidget(feat_item.item, 1, feat_item.w)
            self.feat_items[dname][feat['name']] = feat_item
            self.tree.setItemWidget(feat_item.item, 0, QtWidgets.QLabel(feat['name']))

        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def remove_instr(self, dname):
        if dname in self.feat_items:
            self.feat_items.pop(dname)
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            c = root.child(i)
            if c.text(0) == dname:
                print('Removing device {}'.format(dname))
                root.removeChild(c)
                sip.delete(c)
                c = None
                break
        return


class FeatTreeWidgetItem(QtCore.QObject):
    set_requested = QtCore.pyqtSignal(object) # This signal will be triggered externally when the display value needs to be changed (argument is value)
    go_clicked = QtCore.pyqtSignal() # This signal will be triggered when the "go button" is clicked
    read_clicked = QtCore.pyqtSignal()  # This signal will be triggered when the "read button" is clicked
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
        # print('set_dev', self.dev, self.feat['name'], self.w.getter())
        setattr(self.dev, self.feat['name'], self.w.getter())

    def get_dev(self):
        # print('get_dev', self.dev, self.feat['name'])
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
        self.childs = OrderedDict()
        temp_feat = feat.copy()
        for i,key in enumerate(feat['keys']):
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
    from nspyre.widgets.app import NSpyreApp
    from nspyre.utils import get_configs
    app = NSpyreApp([])
    cfg = get_configs()

    clients = []
    for server in cfg['instrument_servers_addrs']:
        clients.append(Instrument_Server_Client(**server))

    m = Instrument_Manager(clients)
    w = Instrument_Manager_Widget(m)
    w.show()
    app.exec_()