import pymongo
from PyQt5 import QtCore
import pandas as pd

import time
from bson.objectid import ObjectId
from nspyre.utils import get_mongo_client

class DropEvent():
    """Represents a drop of a collection in a certain database"""
    def __init__(self, db, col):
        self.db, self.col = db, col


def modify_df(df, change):
    # print(change)
    if change['operationType'] == 'drop':
        return DropEvent(change['ns']['db'], change['ns']['coll']), None
    key  = change['documentKey']['_id']
    if change['operationType'] == 'update':
        for k, val in change['updateDescription']['updatedFields'].items():
            ks = k.split('.')
            if len(ks) == 1:
                df.loc[key, k] = val
            elif len(ks) == 2:
                #Assume an array here... Will see if we can get away with this
                df.loc[key,ks[0]][int(ks[1])] = val
    elif change['operationType'] == 'insert':
        doc = change['fullDocument']
        _id = doc.pop('_id')
        s = pd.Series(doc, name=_id)
        df = df.append(s)

    else:
        raise NotImplementedError('Cannot modify df with operationType: {}'.format(change['operationType']))
    return df, df.loc[key]


class Mongo_Listenner(QtCore.QThread):
    """Qt Thread which monitors for changes to qither a collection or a database and emits a signal when something happens"""
    updated = QtCore.pyqtSignal(object)
    def __init__(self, db_name, col_name=None, mongo_addrs=None):
        super().__init__()
        self.db_name = db_name
        self.col_name = col_name
        self.mongo_addrs = mongo_addrs
        self.exit_flag = False

    def run(self):
        self.exit_flag = False
        # Connect
        client = get_mongo_client(self.mongo_addrs)
        mongo_obj = client[self.db_name]
        if not self.col_name is None:
            mongo_obj = mongo_obj[self.col_name]

        with mongo_obj.watch() as stream:
            while stream.alive:
                doc = stream.try_next()
                if doc is not None:
                    self.updated.emit(doc)
                if self.exit_flag:
                    return
        if not self.exit_flag:
            self.run() #This takes care of the invalidate event which stops the change_stream cursor

class Synched_Mongo_Collection(QtCore.QObject):
    updated_row = QtCore.pyqtSignal(object) # Emit the updated row
    # mutex = QtCore.QMutex()
    def __init__(self, db_name, col_name, mongo_addrs=None):
        super().__init__()
        self.watcher = Mongo_Listenner(db_name, col_name=col_name, mongo_addr=mongo_addr)
        
        self.col = get_mongo_client(mongo_addrs)[db_name][col_name]
        self.refresh_all()

        self.watcher.start()
        self.watcher.updated.connect(self._update_df)
    
    def refresh_all(self):
        col = list(self.col.find())
        if col == []:
            self.df = None
        else:
            self.df = pd.DataFrame(col)
            self.df.set_index('_id', inplace=True)

    def get_df(self):
        # self.mutex.lock()
        return self.df

    @QtCore.pyqtSlot(object)
    def _update_df(self, change):
        if self.db is None:
            self.refresh_all()
        # print(change)
        self.df, row = modify_df(self.df, change)
        self.updated_row.emit(row)
        # self.refresh_all() #I will make this a little more efficient later on

    def __del__(self):
        self.watcher.exit_flag = True

class Synched_Mongo_Database(QtCore.QObject):
    updated_row = QtCore.pyqtSignal(object, object) # Emit the updated row in the format (col_name, row)
    col_added = QtCore.pyqtSignal(object) # Emit the name of the collection which was added
    col_dropped = QtCore.pyqtSignal(object) # Emit the name of the collection which was dropped
    db_dropped = QtCore.pyqtSignal() #Emitted when the database is dropped

    def __init__(self, db_name, mongo_addrs=None):
        super().__init__()
        self.watcher = Mongo_Listenner(db_name, col_name=None, mongo_addrs=mongo_addrs)
        
        self.db = get_mongo_client(mongo_addrs)[db_name]
        self.refresh_all()

        self.watcher.start()
        self.watcher.updated.connect(self._update)
    
    def refresh_all(self):
        self.dfs = dict()
        for col in self.db.list_collection_names():
            col_data = list(self.db[col].find())
            if not col_data == []:
                self.dfs[col] = pd.DataFrame(col_data)
                self.dfs[col].set_index('_id', inplace=True)

    def get_df(self, col_name, timeout=1):
        try:
            if not self.dfs[col_name] is None:
                return self.dfs[col_name]
        finally:
            t = time.time()
            while time.time()-t<timeout:
                if col_name in self.dfs:
                    return self.dfs[col_name]


    @QtCore.pyqtSlot(object)
    def _update(self, change):
        # print(change)
        if change['operationType'] == 'dropDatabase':
            self.dfs = dict()
            self.db_dropped.emit()
            return
        elif change['operationType'] == 'invalidate':
            return
        col = change['ns']['coll']
        if col in self.dfs:
            df, row = modify_df(self.dfs[col], change)
            if isinstance(df, DropEvent):
                self.dfs.pop(col)
                self.col_dropped.emit(col)
                return
            
            self.dfs[col] = df
            self.updated_row.emit(col, row)
            
        else:
            doc = change['fullDocument']
            row = pd.Series(doc)
            self.dfs[col] = pd.DataFrame([row])
            self.dfs[col].set_index('_id', inplace=True)
            self.col_added.emit(col)

        
        # self.refresh_all() #I will make this a little more efficient later on

    def __del__(self):
        self.watcher.exit_flag = True

    


    
            