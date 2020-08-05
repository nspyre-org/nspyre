# from lantz import Q_
from collections.abc import Iterable
import numpy as np
import inspect
from bson import ObjectId
import yaml
import os
from importlib import import_module
import traceback

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

# TODO unused
def monkey_wrap(wrapped_func, before_func, after_func):
    """Monkey patch technique for wrapping functions defined
    in 3rd party modules, for example:
    import uncontrolled_module
    uncontrolled_module.some_class.internal_method = \
        monkey_wrap(uncontrolled_module.some_class.internal_method, 
                lambda args, kwargs: print('before! args: %s kwargs: %s' % \
                                            (args, kwargs)),
                lambda args, kwargs: print('after!'))
    obj = uncontrolled_module.some_class()
    obj.internal_method(arg1, arg2)
    should return ->
    before! args: (arg1, arg2) kwargs: {}
    <internal_method runs>
    after!"""
    # TODO set original scope wrapped_func = _wrap
    def _wrap(*args, **kwargs):
        if before_func:
            before_func(args, kwargs)
        wrapped_func(*args, **kwargs)
        if after_func:
            after_func(args, kwargs)
    return _wrap

def join_nspyre_path(p):
    """Return an absolute path composed of the root directory plus the argument
    expressed relative to the nspyre root directory"""
    return os.path.join(os.path.dirname(__file__), p)

def get_class_from_str(class_str):
    class_name = class_str.split('.')[-1]
    mod = import_module(class_str.replace('.'+class_name, ''))
    return getattr(mod, class_name)

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