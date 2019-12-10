import pymongo
from lantz import Q_
from collections.abc import Iterable
import numpy as np
import inspect
from bson import ObjectId
import yaml
import os
from importlib import import_module

def get_mongo_client(mongodb_addr=None):
    if mongodb_addr is None:
        cfg = get_configs()
        mongodb_addr = cfg['mongodb_addr']
    return pymongo.MongoClient(mongodb_addr, replicaset='NSpyreSet')
    # for addr in mongodb_addrs:
    #     client = pymongo.MongoClient(addr, re)
    #     if client.is_primary:
    #         print("Connected to Mongo master at: {}".format(addr))
    #         return client
    # raise Exception('Could not find Mongo Master!')

def cleanup_register(client):
    if type(client) is str:
        client = pymongo.MongoClient(client)
    db_list = client['Spyre_Live_Data'].list_collection_names()
    reg_list = [x['_id'] for x in client['Spyre_Live_Data']['Register'].find({},{'_id':True})]
    for name in reg_list:
        if not name in db_list:
            client['Spyre_Live_Data']['Register'].delete_one({'_id': name})

def custom_encode(d):
    out = dict()
    for k,val in d.items():
        if type(val) == Q_:
            out[k] = {'__type__':'Quantity', 'm':val.m, 'units':str(val.units)}
        elif type(val) == RangeDict:
            out[k] = {'__type__':'RangeDict'}
            out[k].update(custom_encode(val))
        elif type(val) == np.ndarray:
            out[k] = {'__type__':'ndarray', 'val':val.tolist()}
        else:
            out[k] = val
    return out

def custom_decode(d):
    out = dict()
    for k,val in d.items():
        if isinstance(val, Iterable) and '__type__' in val:
            if val['__type__'] == 'Quantity':
                out[k] = Q_(val['m'], val['units'])
            elif val['__type__'] == 'RangeDict':
                out[k] = custom_decode(val)
            elif val['__type__'] == 'ndarray':
                out[k] = np.array(val['val'])
        else:
            out[k] = val
    return out

class RangeDict(dict):
    FUNCS = {'linspace':np.linspace, 'arange':np.arange, 'logspace':np.logspace}

    def __init__(self, **initial_dict):
        self._verify_valid(initial_dict)
        dict.__setitem__(self, 'func', initial_dict.pop('func'))
        for k in initial_dict:
            self[k] = initial_dict[k]

    def _verify_valid(self, d):
        # Make sure there is a valid func argument
        if not 'func' in d or d['func'] not in self.FUNCS:
            raise ValueError('RangeDict must have a element <func> in: {}'.format(self.FUNCS.keys()))
        
        # Make sure all required args are define
        signature = inspect.signature(self.FUNCS[d['func']])
        for param in signature.parameters.keys():
            if signature.parameters[param].default == inspect._empty and not param in d:
                raise ValueError('RangeDict does not define required <{}> argument'.format(param))

    def __setitem__(self, key, val):
        if key == 'func':
            raise KeyError('Cannot redefine the func, you should reinstanciate with new parametters')
        elif key in inspect.signature(self.FUNCS[self['func']]).parameters:
            return dict.__setitem__(self, key, val)

    @property
    def array(self):
        d = self.copy()
        func_name = d.pop('func')
        units = None
        for p in d:
            if type(d[p])==Q_:
                if units is None:
                    units = d[p].units
                d[p] = d[p].to(units).m
        if units is None or units == Q_(1, 'dimensionless').units:
            return self.FUNCS[func_name](**d)
        else:
            return self.FUNCS[func_name](**d)*units

def get_configs():
    with open(join_nspyre_path('config.yaml'), 'r') as f:
        d = yaml.safe_load(f)
    # print(d['mongodb_addrs'])
    return d

def join_nspyre_path(path):
    return os.path.join(os.path.dirname(__file__), path)

def get_class_from_str(class_str):
    class_name = class_str.split('.')[-1]
    mod = import_module(class_str.replace('.'+class_name, ''))
    return getattr(mod, class_name)
