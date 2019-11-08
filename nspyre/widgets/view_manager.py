from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

from nspyre.widgets.plotting import LinePlotWidget, HeatmapPlotWidget
from nspyre.widgets.splitter_widget import Splitter, SplitterOrientation
# from nspyre.utils import connect_to_master
from nspyre.mongo_listener import Synched_Mongo_Database
from nspyre.views import Spyrelet_Views
from nspyre.utils import cleanup_register
import pymongo

import numpy as np
import pandas as pd

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
    def __init__(self, mongodb_addr, parent=None):
        super().__init__(parent=parent)
        self.db = Synched_Mongo_Database('Spyre_Live_Data', mongodb_addr)
        # cleanup_register(mongodb_addr)

        self.views = dict()
        self.items = dict()
        
        layout = QtWidgets.QHBoxLayout()
        # Build tree
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setColumnCount(1)
        # self.model = QtGui.QStandardItemModel()
        # self.tree.setModel(self.model)

        self.tree.currentItemChanged.connect(lambda cur, prev: self.new_table_selection(cur))
        layout.addWidget(self.tree)

        # Build layout
        self.plot_layout = QtWidgets.QStackedLayout()
        plot_container = QtWidgets.QWidget()
        plot_container.setLayout(self.plot_layout)

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
        # self.db.col_dropped.connect(self.del_col)
        self.db.updated_row.connect(self.update_plot)

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
        self.items[col_name] = {'__top':top}
        self.views[col_name] = dict()

        for name, view in spyrelet_views.get_1D_views().items():
            self.views[col_name][name] = LinePlotView(view)
            self.items[col_name][name] = QtWidgets.QTreeWidgetItem(0)#QtGui.QStandardItem(name)
            self.items[col_name][name].setText(0, name)
            
            self.plot_layout.addWidget(self.views[col_name][name].w)
            top.addChild(self.items[col_name][name])

        self.tree.insertTopLevelItem(0, top)
        # self.update_plot(col_name, None)

    

        # self.line_plot = 
        # self.img_plot = HeatmapPlotWidget()
        # 
        # self.plot_layout.addWidget(self.img_plot)
        # self.plot_container = QtWidgets.QWidget()
        # self.plot_container.setLayout(self.plot_layout)

    def new_table_selection(self, item):
        txt = item.text(0)
        if not txt in self.views:
            spyrelet_name = item.parent().text(0)
            view_name = txt
        else:
            # Selected a top level item
            return
        self.plot_layout.setCurrentWidget(self.views[spyrelet_name][view_name].w)
        self.views[spyrelet_name][view_name].start_updating()
        if spyrelet_name in self.db.dfs:
            self.update_plot(spyrelet_name, None)

        
        # if not item is None:
        #     self.plot_layout.setCurrentWidget(self.line_plot)
        #     self.tabulate_item(item)
        #     self.plot_item(item)








# class DataExplorer(QtWidgets.QWidget):
#     def __init__(self, parent=None, filename=None):
#         super().__init__(parent=parent)
#         self.repo = None
#         self.item_list = list()
#         self.filename = filename
#         self.build_ui()
#         if not filename is None:
#             self.reload()

#     def build_ui(self):

#         # Build file loading widgets
#         ctrl_panel = QtWidgets.QWidget()
#         layout = QtWidgets.QVBoxLayout()
#         ctrl_panel.setLayout(layout)
#         select_filename_btn = QtWidgets.QPushButton('Select File...')
#         self.filename_label = QtWidgets.QLabel('No file selected' if self.filename is None else self.filename)
#         select_filename_btn.clicked.connect(self.select_filename)
#         reload_btn = QtWidgets.QPushButton('Reload')
#         reload_btn.clicked.connect(self.reload)
#         layout.addWidget(select_filename_btn)
#         layout.addWidget(self.filename_label)
#         layout.addWidget(reload_btn)

#         #Navigation function
#         def move_index_down(_self, _ev):
#             if type(_ev)==QtGui.QKeyEvent:
#                 if _ev.matches(QtGui.QKeySequence.MoveToPreviousPage):
#                     inc = -1
#                 elif _ev.matches(QtGui.QKeySequence.MoveToNextPage):
#                     inc = 1
#                 else:
#                     return QtWidgets.QTreeWidget.keyPressEvent(_self, _ev)
#                 cur = self.tree.currentItem()
#                 if not cur is None:
#                     name = cur.text(0)
#                     i = self.item_list.index(cur)
#                     found_match = False
#                     while not found_match:
#                         i+=inc
#                         if i >=len(self.item_list) or i<0:
#                             found_match = True
#                         elif self.item_list[i].text(0)==name:
#                             self.tree.setCurrentItem(self.item_list[i])
#                             found_match = True
#                 _ev.accept()

#         # Build tree
#         self.tree = QtWidgets.QTreeWidget()
#         self.tree.currentItemChanged.connect(lambda cur, prev: self._new_table_selection(cur))
#         layout.addWidget(self.tree)
#         self.tree.keyPressEvent = lambda ev: move_index_down(self.tree, ev)

#         # Build plot widgets
#         self.plot_layout = QtWidgets.QStackedLayout()
#         self.line_plot = LinePlotWidget()
#         self.img_plot = HeatmapPlotWidget()
#         self.plot_layout.addWidget(self.line_plot)
#         self.plot_layout.addWidget(self.img_plot)
#         self.
#         self.plot_container.setLayout(self.plot_layout)

#         #Build dataframe table
#         self.df_table = QtWidgets.QTableView()
        
#         self.tab_container = QtWidgets.QTabWidget()
#         self.tab_container.addTab(self.plot_container, 'Plot')
#         self.tab_container.addTab(self.df_table, 'Table')

#         #Set the main layout
#         splitter_config = {
#             'main_w': ctrl_panel,
#             'side_w': self.tab_container,
#             'orientation': SplitterOrientation.vertical_right_button,
#         }
#         splitter = Splitter(**splitter_config)

#         splitter.setSizes([1, 400])
#         splitter.setHandleWidth(10)

#         layout = QtWidgets.QHBoxLayout()
#         layout.addWidget(splitter)
#         self.setLayout(layout)

#     def _new_table_selection(self, item):
#         if not item is None:
#             self._tabulate_item(item)
#             self._plot_item(item)

#     def _tabulate_item(self, item):
#         path = item.data(0,QtCore.Qt.ToolTipRole)
#         if path=='/':
#             df = self.repo.get_index(col_order=['uid', 'name', 'spyrelet', 'date', 'time', 'description'])
#             pd_model = PandasModel(df)
#             model = QtCore.QSortFilterProxyModel()
#             model.setSourceModel(pd_model)
#             self.df_table.setSortingEnabled(True)
#             self.tab_container.setCurrentWidget(self.df_table)
#         else:
#             df = self.repo[path].get_data()
#             self.df_table.setSortingEnabled(False)
#             if df is None:
#                 model = PandasModel(pd.DataFrame({}))
#             else:
#                 model = PandasModel(df)
#         self.df_table.setModel(model)

#     def _plot_item(self, item):
#         path = item.data(0,QtCore.Qt.ToolTipRole)
#         self.plot_node(self.repo[path])

#     def plot_node(self, node):
#         meta = node.get_meta()
#         if 'BasePlotWidget_type' in meta:
#             if node.get_data() is None or node.get_data().empty:
#                 return
#             if meta['BasePlotWidget_type'] == self.line_plot.plot_type_str:
#                 self.plot_layout.setCurrentWidget(self.line_plot)
#                 self.line_plot.load_node(node)
#             elif meta['BasePlotWidget_type'] == self.img_plot.plot_type_str:
#                 self.plot_layout.setCurrentWidget(self.img_plot)
#                 self.img_plot.load_node(node)
#             self.tab_container.setCurrentWidget(self.plot_container)


#     def select_filename(self):
#         filename, other = QtWidgets.QFileDialog.getOpenFileName(None, 'Save repository to...', '', 'HDF5 files (*.h5)')
#         if filename:
#             self.filename_label.setText(filename)
#             self.filename = filename
#             self.reload()
#         return

#     def reload(self):
#         if self.filename is None:
#             raise Exception('No file selected.  Please select a filename')
#         self.repo = Repository(self.filename)
#         self._plot_item = lambda _s,_i: None
#         self.tree.clear()
#         self.tree.addChild = self.tree.addTopLevelItem
#         self.item_list = list()
#         def add_child(node, parent, path_prefix):
#             for name in node.get_child_names(sort=True):
#                 child = node.get_child(name)
#                 path = path_prefix + '/' + name
#                 tree_item = QtWidgets.QTreeWidgetItem([name])
#                 tree_item.setData(0, QtCore.Qt.ToolTipRole, path)
#                 parent.addChild(tree_item)
#                 self.item_list.append(tree_item)
#                 add_child(child, tree_item, path)
#         tree_item = QtWidgets.QTreeWidgetItem(['root'])
#         tree_item.setData(0, QtCore.Qt.ToolTipRole, '/')
#         self.tree.addChild(tree_item)
#         self.item_list.append(tree_item)
#         add_child(self.repo.root, self.tree, '')
#         self._plot_item = lambda item: self.__class__._plot_item(self, item)

#     def get_selection_str(self, col_sep='\t', row_sep='\n'):
#         indexes = self.df_table.selectedIndexes()
#         model = self.df_table.model()
#         if model is None:
#             return
#         if len(indexes) == 0:
#             df = model._data
#             return df.to_csv(sep=col_sep)
#         else:
#             indexes = sorted(indexes, key=lambda idx:(idx.row(),idx.column()))
#             nb_column = indexes[-1].column()-indexes[0].column()+1
#             model = self.df_table.model()
#             ans = ''
#             for i, index in enumerate(indexes):
#                 ans += model.data(index)
#                 if (i+1)%nb_column == 0:
#                     ans += row_sep
#                 else:
#                     ans += col_sep
#             return ans


#     def keyPressEvent(self, ev):
#         if type(ev)==QtGui.QKeyEvent:
#             if ev.matches(QtGui.QKeySequence.Copy):
#                 app = QtWidgets.QApplication.instance()
#                 app.clipboard().setText(self.get_selection_str())
#                 ev.accept()
#             if ev.matches(QtGui.QKeySequence.Save):
#                 filename, other = QtWidgets.QFileDialog.getSaveFileName(None, 'Save this table to...', '', 'Comma Separated Value (*.csv)')
#                 if filename:
#                     df = self.df_table.model()._data
#                     df.to_csv(path_or_buf=filename, sep=',')
#                 ev.accept()



if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = View_Manager(mongodb_addr="mongodb://localhost:27017/")
    w.show()
