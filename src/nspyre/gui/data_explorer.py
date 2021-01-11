#!/usr/bin/env python
"""
    ?

    Author: Alexandre Bourassa
"""

###########################
# imports
###########################

# std
import os
import logging

# 3rd party
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication
import pandas as pd

# nspyre
from nspyre.gui.view_manager import ViewManagerWindow
from nspyre.gui.widgets.splitter_widget import Splitter, SplitterOrientation
from nspyre.gui.data_handling import load_data

###########################
# globals
###########################

logger = logging.getLogger(__name__)

###########################
# classes
###########################

class Permanent_QFileDialog(QtWidgets.QFileDialog):
    def done(self, r):
        print('done')

class Local_json_DB(QtCore.QObject):
    """This essentially emulates a nspyre.mongo_listner.Synched_Mongo_Database by implementing
    a dfs proprety and a get_df function"""
    updated_row = QtCore.pyqtSignal(object, object) # Emit the updated row in the format (col_name, row)
    col_added = QtCore.pyqtSignal(object) # Emit the name of the collection which was added
    col_dropped = QtCore.pyqtSignal(object) # Emit the name of the collection which was dropped
    db_dropped = QtCore.pyqtSignal() #Emitted when the database is dropped

    def __init__(self, filename=None):
        super().__init__()
        self.dfs = dict()
        if not filename is None:
            self.load(filename)

    def load(self, filename):
        self.clear()
        d = load_data(filename)
        # name = d['name']
        # description = d['description']

        self.dfs = {d['spyrelet_name']:d['data']}
        self.dfs['Register'] = pd.DataFrame({'_id':[d['spyrelet_name']],'class':[d['spyrelet_class']]}).set_index('_id')
        self.col_added.emit(d['spyrelet_name'])

        for cname in d['children']:
            num = len(d['children'][cname]['data_list'])
            for i in range(num):
                cclass = d['children'][cname]['spyrelet_class']
                cdata = d['children'][cname]['data_list'][i]
                self.add_df('{}_{}'.format(cname, i), cdata, cclass)
        return d
                
    
    def add_df(self, name, df, sclass):
        reg_df = pd.DataFrame({'_id':[name], 'class':[sclass]}).set_index('_id')
        self.dfs['Register'] = self.dfs['Register'].append(reg_df)
        self.dfs[name] = df
        self.col_added.emit(name)

    def drop_df(self, name):
        self.dfs.pop(name)
        self.col_dropped.emit(name)

    def clear(self):
        for name in list(self.dfs.keys()):
            self.drop_df(name)

    def get_df(self, df_name):
        return self.dfs[df_name]



class Data_Explorer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.db = Local_json_DB()
        layout = QtWidgets.QVBoxLayout()
        self.view_manager = ViewManagerWindow(db=self.db, react_to_drop=True)
        self.file_browser = Permanent_QFileDialog(filter = '*.json')
        
        hsplitter = Splitter(main_w=self.file_browser, side_w=self.view_manager, orientation=SplitterOrientation.vertical_right_button)
        hsplitter.setSizes([1, 400])
        hsplitter.setHandleWidth(10)
        layout.addWidget(hsplitter)
        self.setLayout(layout)

        self.file_browser.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        self.file_browser.fileSelected.connect(self.load_file)
        self.file_browser.currentChanged.connect(self.load_file)
        self.show()

    def load_file(self, filename):
        if not os.path.isfile(filename):
            return
        sname, vname = self.view_manager.get_view_name(self.view_manager.tree.currentItem())
        print('Loading {}'.format(filename))
        d = self.db.load(filename)
        if sname in self.view_manager.items:
            if vname in self.view_manager.items[sname]:
                item = self.view_manager.items[sname][vname]
            else:
                item = self.view_manager.items[sname]['__top']
        else:
            # Open the first plot in the main spyrelet
            sname = d['spyrelet_name']
            view_names = list(self.view_manager.items[sname].keys())
            view_names.sort()
            # view_names.pop('__top')
            item = self.view_manager.items[sname][view_names[1]] # Element 0 should be __top
        self.view_manager.tree.setCurrentItem(item)


if __name__ ==  '__main__':
    import logging
    import sys
    from PyQt5.QtCore import Qt
    from nspyre.gui.app import NSpyreApp
    from nspyre.misc.logging import nspyre_init_logger

    nspyre_init_logger(logging.INFO)

    logger.info('starting Data Explorer...')
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = NSpyreApp([sys.argv])
    data_explorer = Data_Explorer()
    sys.exit(app.exec())
