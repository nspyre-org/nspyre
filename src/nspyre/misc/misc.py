from collections.abc import Iterable
import functools
import importlib
import inspect
import sys
import warnings

import numpy as np
import pymongo
import rpyc

from nspyre.definitions import Q_, MONGO_RS, CONFIG_MONGO_ADDR_KEY
from nspyre.config.config_files import load_meta_config, load_config, get_config_param

string_types = (type(b''), type(u''))


def deprecated(reason):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """

    if isinstance(reason, string_types):

        # The @deprecated is used with a 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated("please, use another function")
        #    def old_function(x, y):
        #      pass

        def decorator(func1):

            if inspect.isclass(func1):
                fmt1 = "Call to deprecated class {name} ({reason})."
            else:
                fmt1 = "Call to deprecated function {name} ({reason})."

            @functools.wraps(func1)
            def new_func1(*args, **kwargs):
                warnings.simplefilter('always', DeprecationWarning)
                warnings.warn(
                    fmt1.format(name=func1.__name__, reason=reason),
                    category=DeprecationWarning,
                    stacklevel=2
                )
                warnings.simplefilter('default', DeprecationWarning)
                return func1(*args, **kwargs)

            return new_func1

        return decorator

    elif inspect.isclass(reason) or inspect.isfunction(reason):

        # The @deprecated is used without any 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated
        #    def old_function(x, y):
        #      pass

        func2 = reason

        if inspect.isclass(func2):
            fmt2 = "Call to deprecated class {name}."
        else:
            fmt2 = "Call to deprecated function {name}."

        @functools.wraps(func2)
        def new_func2(*args, **kwargs):
            warnings.simplefilter('always', DeprecationWarning)
            warnings.warn(
                fmt2.format(name=func2.__name__),
                category=DeprecationWarning,
                stacklevel=2
            )
            warnings.simplefilter('default', DeprecationWarning)
            return func2(*args, **kwargs)

        return new_func2

    else:
        raise TypeError(repr(type(reason)))


def register_quantity_brining(quantity_class):
    """pint has an associated unit registry, and Quantity objects 
    cannot be shared between registries. Because Quantity objects 
    passed from the client to server or vice versa have a different 
    unit registry, they must be converted to Quantity objects of the 
    local registry. RPyC serializes objects using "brine". We will 
    make a custom brine serializer for Quantity objects to properly 
    pack and unpack them using the local unit registry.
    For more details, see pint documentation and
    https://github.com/tomerfiliba-org/rpyc/blob/master/rpyc/core/brine.py

    quantity_class: the Quantity class object from the local pint registry
    """
    rpyc.core.brine.TAG_PINT_Q = b"\xFA"

    # function for serializing quantity objects
    @rpyc.core.brine.register(rpyc.core.brine._dump_registry,
                                type(quantity_class(1, 'V')))
    def _dump_quantity(obj, stream):
        stream.append(rpyc.core.brine.TAG_PINT_Q)
        quantity_tuple = obj.to_tuple()
        rpyc.core.brine._dump((float(quantity_tuple[0]), \
                                quantity_tuple[1]), stream)

    # function for deserializing quantity objects
    @rpyc.core.brine.register(rpyc.core.brine._load_registry,
                            rpyc.core.brine.TAG_PINT_Q)
    def _load_quantity(stream):
        q = quantity_class.from_tuple(rpyc.core.brine._load(stream))
        return q
    rpyc.core.brine.simple_types = rpyc.core.brine.simple_types.union(\
                                    frozenset([type(quantity_class(1, 'V'))]))


def load_class_from_str(class_str):
    """Load a python class object (available in the local scope)
    from a string"""
    class_name = class_str.split('.')[-1]
    module_name = class_str.replace('.' + class_name, '')
    if module_name in sys.modules:
        # we just need to reload it
        mod = importlib.reload(sys.modules[module_name])
    else:
        # load the module
        mod = importlib.import_module(module_name)
    return getattr(mod, class_name)


def load_class_from_file(file_path, class_name):
    """Load a python class object from an external python file"""
    file_dir = file_path.parent
    file_name = str(file_path.name)
    # remove .py extension
    file_name = file_name.split('.py')[0]
    # load the spyrelet class from its python file
    sys.path.append(str(file_dir))
    if file_name in sys.modules:
        loaded_module = importlib.reload(sys.modules[file_name])
    else:
        loaded_module = importlib.import_module(file_name)
    loaded_class = getattr(loaded_module, class_name)
    return loaded_class


def qt_set_trace():
    """Set a tracepoint in the Python debugger that works with Qt"""
    from PyQt5.QtCore import pyqtRemoveInputHook
    from pdb import set_trace
    pyqtRemoveInputHook()
    set_trace()


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
    if isinstance(d, list):
        out = []
        for val in d:
            if isinstance(val, Iterable) and '__type__' in val:
                if val['__type__'] == 'Quantity':
                    out.append(Q_(val['m'], val['units']))
                elif val['__type__'] == 'RangeDict':
                    out.append(custom_decode(val))
                elif val['__type__'] == 'ndarray':
                    out.append(np.array(val['val']))
            else:
                out.append(val)
        return out
    else:
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

@deprecated('Use a normal numpy.linspace, numpy.arange, or numpy.logspace. This will be removed in a future version of nspyre.')
class RangeDict(dict):
    FUNCS = {'linspace': np.linspace, 'arange': np.arange, 'logspace': np.logspace}

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
            raise KeyError('Cannot redefine the func, you should reinstantiate with new parameters')
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


def get_mongo_client(mongodb_addr=None):
    if mongodb_addr is None:
        cfg_path = load_meta_config()
        cfg = load_config(cfg_path)
        mongodb_addr, _ = get_config_param(cfg, [CONFIG_MONGO_ADDR_KEY])
    return pymongo.MongoClient(mongodb_addr, replicaset=MONGO_RS)
