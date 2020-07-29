from pint import Quantity as Q_
from collections.abc import Iterable
import numpy as np
import inspect
from bson import ObjectId
import yaml
import os
import sys
from importlib import import_module
import traceback
from nspyre.definitions import _join_nspyre_path, CLIENT_META_CONFIG_YAML, \
                                MONGO_RS
import pymongo

class MonkeyWrapper():
    """Monkey patch technique for wrapping objects defined
    in 3rd party modules, for example:
    ----------------------------------
    import uncontrolled_module
    def get_override(obj, attr):
        ret = getattr(obj, attr)
        print('got object %s attribute %s = %s' % (obj, attr, ret))
        return ret
    def set_override(obj, attr, val):
        print('setting object %s attribute %s to %s' % (obj, attr, val))
        setattr(obj, attr, val)
    obj = uncontrolled_module.some_class()
    wrapped_obj = MonkeyWrapper(obj,
                                get_attr_override=get_override,
                                set_attr_override=set_override)
    wrapped_obj.internal_attribute = 5
    a = wrapped_obj.internal_attribute
    -------- should return -> --------
    setting object <obj> attribute internal_attribute to 5
    got object <obj> attribute internal_attribute = 5
    """
    def __init__(self, wrapped_obj,
                    get_attr_override=None,
                    set_attr_override=None):
        """ """
        # we can't use self.<instance_var> because that will call __setattr__
        # and __getattr__, so we have to get/set our instance variables
        # using __dict__
        self.__dict__['wrapped_obj'] = wrapped_obj
        self.__dict__['get_attr_override'] = get_attr_override
        self.__dict__['set_attr_override'] = set_attr_override

    def __getattr__(self, attr):
        """Override the wrapped object's getattr(); call our custom 
        monkey-wrapping function instead, if defined"""
        if self.__dict__['get_attr_override']:
            return self.__dict__['get_attr_override']\
                    (self.__dict__['wrapped_obj'], attr)
        else:
            return getattr(self.__dict__['wrapped_obj'], attr)

    def __setattr__(self, attr, val):
        """Override the wrapped object's set_attr(); call our custom 
        monkey-wrapping function instead, if defined"""
        if self.__dict__['set_attr_override']:
            self.__dict__['set_attr_override']\
                (self.__dict__['wrapped_obj'], attr, val)
        else:
            setattr(self.__dict__['wrapped_obj'], attr, val)

def load_class_from_str(class_str):
    """Return a python class object from a string"""
    class_name = class_str.split('.')[-1]
    mod = import_module(class_str.replace('.' + class_name, ''))
    return getattr(mod, class_name)

def join_nspyre_path(path):
    """Return a full path from a path given relative to the nspyre root 
    directory"""
    return _join_nspyre_path(path)

# def get_class_from_str(class_str):
#     class_name = class_str.split('.')[-1]
#     mod = import_module(class_str.replace('.'+class_name, ''))
#     return getattr(mod, class_name)

    # for addr in mongodb_addrs:
    #     client = pymongo.MongoClient(addr, re)
    #     if client.is_primary:
    #         print("Connected to Mongo master at: {}".format(addr))
    #         return client
    # raise Exception('Could not find Mongo Master!')

# def cleanup_register(client):
#     if type(client) is str:
#         client = pymongo.MongoClient(client)
#     db_list = client['Spyre_Live_Data'].list_collection_names()
#     reg_list = [x['_id'] for x in client['Spyre_Live_Data']['Register'].find({},{'_id':True})]
#     for name in reg_list:
#         if not name in db_list:
#             client['Spyre_Live_Data']['Register'].delete_one({'_id': name})

# def custom_encode(d):
#     out = dict()
#     for k,val in d.items():
#         if type(val) == Q_:
#             out[k] = {'__type__':'Quantity', 'm':val.m, 'units':str(val.units)}
#         elif type(val) == RangeDict:
#             out[k] = {'__type__':'RangeDict'}
#             out[k].update(custom_encode(val))
#         elif type(val) == np.ndarray:
#             out[k] = {'__type__':'ndarray', 'val':val.tolist()}
#         else:
#             out[k] = val
#     return out

# def custom_decode(d):
#     out = dict()
#     for k,val in d.items():
#         if isinstance(val, Iterable) and '__type__' in val:
#             if val['__type__'] == 'Quantity':
#                 out[k] = Q_(val['m'], val['units'])
#             elif val['__type__'] == 'RangeDict':
#                 out[k] = custom_decode(val)
#             elif val['__type__'] == 'ndarray':
#                 out[k] = np.array(val['val'])
#         else:
#             out[k] = val
#     return out


# def arange(start, stop, step, dtype=None):
#     return np.arange(start, stop, step, dtype=dtype)

# class RangeDict(dict):
#     FUNCS = {'linspace':np.linspace, 'arange':arange, 'logspace':np.logspace}

#     def __init__(self, **initial_dict):
#         self._verify_valid(initial_dict)
#         dict.__setitem__(self, 'func', initial_dict.pop('func'))
#         for k in initial_dict:
#             self[k] = initial_dict[k]

#     def _verify_valid(self, d):
#         # Make sure there is a valid func argument
#         if not 'func' in d or d['func'] not in self.FUNCS:
#             raise ValueError('RangeDict must have a element <func> in: {}'.format(self.FUNCS.keys()))
        
#         # Make sure all required args are define
#         signature = inspect.signature(self.FUNCS[d['func']])
#         for param in signature.parameters.keys():
#             if signature.parameters[param].default == inspect._empty and not param in d:
#                 raise ValueError('RangeDict does not define required <{}> argument'.format(param))

#     def __setitem__(self, key, val):
#         if key == 'func':
#             raise KeyError('Cannot redefine the func, you should reinstanciate with new parametters')
#         elif key in inspect.signature(self.FUNCS[self['func']]).parameters:
#             return dict.__setitem__(self, key, val)

#     @property
#     def array(self):
#         d = self.copy()
#         func_name = d.pop('func')
#         units = None
#         for p in d:
#             if type(d[p])==Q_:
#                 if units is None:
#                     units = d[p].units
#                 d[p] = d[p].to(units).m
#         if units is None or units == Q_(1, 'dimensionless').units:
#             return self.FUNCS[func_name](**d)
#         else:
#             return self.FUNCS[func_name](**d)*units

def get_configs(filename=None):
    if not filename:
        filename = join_nspyre_path(CLIENT_META_CONFIG_YAML)
    cfg,_ = load_config(filename)
    return cfg

def get_mongo_client(mongodb_addr=None):
    if mongodb_addr is None:
        cfg = get_configs()
        mongodb_addr = cfg['mongodb_addr']
    return pymongo.MongoClient(mongodb_addr, replicaset=MONGO_RS)

def load_all_spyrelets():
    cfg = get_configs()
    names = list(cfg['experiment_list'].keys())

    ans = dict()
    last_len = -1
    while last_len != len(ans):
        last_len = len(ans)
        for sname in names:
            exp = cfg['experiment_list'][sname]
            subs = exp['spyrelets'] if 'spyrelets' in exp else {}
            if not sname in ans and all([x in ans for x in list(subs.values())]):
                try:
                    sclass = get_class_from_str(exp['class'])
                    subs = {name:ans[inst_name] for name, inst_name in subs.items()}
                    args = exp['args'] if 'args' in exp else {}
                    args = custom_decode(args)
                    ans[sname] = sclass(sname, spyrelets=subs, **args)
                except:
                    print("Could not instanciate spyrelet {}...".format(sname))
                    traceback.print_exc()

        for sname in names:
            if not sname in ans:
                subs = cfg['experiment_list'][sname]['spyrelets'] if 'spyrelets' in exp else {}
                print("Could not instanciate spyrelet {}...  This is possibly because of missing sub-spyrelet: {}".format(sname, subs))
    return ans

def drop_spyrelet(name, client=None):
    if client is None: client = get_mongo_client()
    client['Spyre_Live_Data'][name].drop()
    client['Spyre_Live_Data']['Register'].delete_one({'_id': name})

def drop_all_spyrelets(except_list=[], client=None):
    if client is None: client = get_mongo_client()
    all_in_reg = [x['_id'] for x in client['Spyre_Live_Data']['Register'].find({},{})]
    for name in all_in_reg:
        if not name in except_list:
            drop_spyrelet(name, client=client)