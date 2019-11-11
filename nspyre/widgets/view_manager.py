from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

from nspyre.widgets.plotting import LinePlotWidget, HeatmapPlotWidget
from nspyre.widgets.splitter_widget import Splitter, SplitterOrientation
# from nspyre.utils import connect_to_master
from nspyre.mongo_listener import Synched_Mongo_Database
from nspyre.views import Spyrelet_Views
from nspyre.utils import cleanup_register, join_nspyre_path
import pymongo

import numpy as np
import pandas as pd
import time

class LinePlotView():
    def __init__(self, view):
        if view.type != '1D':
            raise "This class is for 1D plot only"
        self.w = LinePlotWidget()
        self.view = view
        self.is_updating = False
        self.update_fun = view.update_fun
        self.init_formatter = view.get_formatter(self.w, 'init')
        self.update_formatter = view.get_formatter(self.w, 'update')
        if not self.init_formatter is None:
            self.init_formatter(self.w)

            

    def start_updating(self):
        self.is_updating = True

    def stop_updating(self):
        self.is_updating = False

    def update(self, df):
        if self.is_updating:
            traces = self.update_fun(df)
            for name, data in traces.items():
                self.w.set(name, xs=data[0], ys=data[1])
            if not self.update_formatter is None:
                self.update_formatter(self.w)
        

class View_Manager(QtWidgets.QWidget):
    def __init__(self, mongodb_addr, parent=None, db_name='Spyre_Live_Data', react_to_drop=False):
        super().__init__(parent=parent)
        self.db = Synched_Mongo_Database(db_name, mongodb_addr)
        # cleanup_register(mongodb_addr)

        self.views = dict()
        self.items = dict()
        self.last_updated = dict()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_colors)
        self.timer.start(100)
        self.fade_rate = 2
        
        layout = QtWidgets.QHBoxLayout()
        # Build tree
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)

        self.tree.currentItemChanged.connect(self.new_table_selection)
        layout.addWidget(self.tree)

        # Build layout
        self.plot_layout = QtWidgets.QStackedLayout()
        plot_container = QtWidgets.QWidget()
        plot_container.setLayout(self.plot_layout)
        self.default_image = ImageWidget(join_nspyre_path('images/logo.jpg'))
        self.plot_layout.addWidget(self.default_image)


        splitter_config = {
            'main_w': self.tree,
            'side_w': plot_container,
            'orientation': SplitterOrientation.vertical_right_button,
        }
        splitter = Splitter(**splitter_config)

        splitter.setSizes([1, 400])
        splitter.setHandleWidth(10)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

        if 'Register' in self.db.dfs:
            for name in self.db.get_df('Register').index:
                self.add_col(name)


        #Connect db signals
        self.db.col_added.connect(self.add_col)
        self.db.updated_row.connect(self._update_plot)
        if react_to_drop:
            self.db.col_dropped.connect(self.del_col)

    def _update_plot(self, col_name, row):
        if col_name != 'Register':
            self.last_updated[col_name] = time.time()
        self.update_plot(col_name, row)

    def update_plot(self, col_name, row):
        if col_name == 'Register':
            self.add_col(row.name)
            return
        for name, view in self.views[col_name].items():
            view.update(self.db.get_df(col_name))
        
        
    def add_col(self, col_name):
        if col_name == 'Register':
            return
        sclass = self.db.get_df('Register').loc[col_name]['class']
        spyrelet_views = Spyrelet_Views(sclass)
        
        if col_name in self.views:
            return
        top = QtWidgets.QTreeWidgetItem(self.tree, [col_name])
        self.default_color = top.background(0) # This is used to remember the default color when instanciating (to restore in update_color)

        self.items[col_name] = {'__top':top}
        self.views[col_name] = dict()
        self.last_updated[col_name] = time.time()

        for name, view in spyrelet_views.get_1D_views().items():
            self.views[col_name][name] = LinePlotView(view)
            self.items[col_name][name] = QtWidgets.QTreeWidgetItem(0)#QtGui.QStandardItem(name)
            self.items[col_name][name].setText(0, name)
            
            self.plot_layout.addWidget(self.views[col_name][name].w)
            top.addChild(self.items[col_name][name])

        self.tree.insertTopLevelItem(0, top)

    def del_col(self, col_name):
        if col_name == 'Register':
            return
        for pname, view in self.views[col_name].items():
            self.plot_layout.removeWidget(view.w)
            view.w.deleteLater()
        for iname, item in self.items[col_name].items():
            self.tree.removeItemWidget(item,0)
        self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(self.items[col_name]['__top']))
        self.views.pop(col_name)
        self.items.pop(col_name)
        self.last_updated.pop(col_name)
    

    def new_table_selection(self, cur, prev):
        def get_view_name(item):
            if item is None:
                return None, None
            txt = item.text(0)
            if not txt in self.views:
                spyrelet_name = item.parent().text(0)
                view_name = txt
                return spyrelet_name, view_name
            else:
                # Selected a top level item
                return txt, None
        spyrelet_name, view_name = get_view_name(cur)
        spyrelet_name_old, view_name_old = get_view_name(prev)
        if not view_name_old is None:
            self.views[spyrelet_name_old][view_name_old].stop_updating()
        if view_name is None:
            # Selected a top level item
            self.plot_layout.setCurrentWidget(self.default_image)
            return
        
        self.plot_layout.setCurrentWidget(self.views[spyrelet_name][view_name].w)
        self.views[spyrelet_name][view_name].start_updating()
        if spyrelet_name in self.db.dfs:
            self.update_plot(spyrelet_name, None)

    def update_colors(self):
        try:
            for col_name, last_time in self.last_updated.items():
                delta = (time.time()-last_time)/self.fade_rate
                if delta<1:
                    color = QtGui.QColor(0, 255, 0, int(max((1-delta)*255,0)))
                    self.items[col_name]['__top'].setBackground(0, QtGui.QBrush(color))
                else:
                    self.items[col_name]['__top'].setBackground(0, self.default_color)
        except:
            pass

class ImageWidget(QtWidgets.QWidget):
    def __init__(self, filename, parent=None):
        super().__init__(parent=parent)
        label = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap(filename)
        label.setPixmap(pixmap)

        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(label,0,1) #add the widget in the second colum
        layout.setColumnStretch(0,1) #set stretch of first
        layout.setColumnStretch(2,1) #and third column
        self.setLayout(layout)

if __name__ == '__main__':
    from nspyre.widgets.app import NSpyreApp
    from nspyre.utils import get_configs
    app = NSpyreApp([])
    cfg = get_configs()
    w = View_Manager(mongodb_addr=cfg['mongodb_addrs'][0], react_to_drop=False)
    w.show()
    app.exec_()
