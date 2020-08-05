"""
    nspyre.spyrelet.spyrelet.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    This module defines the base functionality of spyrelets, which are scripts
    that encode the experimental logic.

    Author: Alexandre Bourassa
    Date: 10/30/2019
    Modified: Jacob Feder 7/11/2020
"""

# std
import threading
from collections import OrderedDict
import traceback
import inspect

# 3rd party
import pymongo
import pandas as pd
import numpy as np
from lantz import Q_
from pint.util import infer_base_unit
from tqdm.auto import tqdm

# nspyre
from nspyre.gui.data_handling import save_data
from nspyre.instrument_manager import Instrument_Manager
from nspyre.utils import *

###########################
# Exceptions
###########################

class MissingDeviceError(Exception):
    pass

class MissingSpyreletError(Exception):
    pass

class StopRunning(Exception):
    pass

###########################
# Classes / functions
###########################

class Spyrelet():
    """
    A few notes about the spyrelet class:
        - This is the class you need to subclass for making experiments.
        - All devices used in the spyrelet must be listed in the
            REQUIRED_DEVICES dict
        - All sub-spyrelet must also be listed in the REQUIRED_SPYRELETS dict
        - Upon instantiation the class will check the __init__ arguments
            devices and spyrelets to make sure they satisfy these requirements
        - For higher performance we will store the data internally as a list
            instead of a dataframe.  Quicker to append to a list.
    """

    # A dict with the names and associated class of the devices required to run
    # this spyrelet
    REQUIRED_DEVICES = dict()

    # A dict with the name and associated class of the sub-spyrelet required to
    # run this spyrelet
    REQUIRED_SPYRELETS = dict()

    # A definition of the parametters that are used as arguments to the
    # main/initialize/finalize functions. These are used both to generate a
    # launcher GUI and to enforce units at call time.
    PARAMS = dict()

    # An extra dictionary, which can be defined by the user at initialization
    # time. This can store anything the users want
    CONSTS = dict()

    def __init__(self, unique_name, manager, spyrelets={}, device_alias={},
                    mongodb_addr=None, **consts):
        self.name = unique_name
        self.progress = tqdm
        self.spyrelets = spyrelets
        self.CONSTS = self.CONSTS.copy()
        self.CONSTS.update(**consts)
        self.last_kwargs = dict()

        self.mongodb_addr = mongodb_addr
        self.validate()
        
        reg_entry = {
            '_id':unique_name,
            'class':"{}.{}".format(self.__class__.__module__, self.__class__.__name__),
        }

        self.client = get_mongo_client(mongodb_addr)
        self.col = self.client['Spyre_Live_Data'][unique_name]
        self.client['Spyre_Live_Data']['Register'].update_one({'_id':unique_name},{'$set':reg_entry}, upsert=True)
        self.clear_data()

        # This is imported here otherwise the import may occur before the Remote_Device_Instance is dynamically generated...
        # from instrument_server import Remote_Device

        devices = manager.get_devices()
        for dname, dclass in self.REQUIRED_DEVICES.items():
            real_dname = device_alias[dname] if dname in device_alias else dname
            if real_dname in devices:
                # isRemoteDevice = issubclass(type(devices[dname]), Remote_Device)
                #This is a convoluted way of checking subclass
                isRemoteDevice = any(['spyre.instrument_server.Remote_Device' in str(c) for c in inspect.getmro(type(devices[real_dname]))])

                if isRemoteDevice :
                    inst_dclass = get_class_from_str(devices[real_dname].info['class'])
                    dev = devices[real_dname]
                else:
                    inst_dclass = type(devices[real_dname])
                    dev = devices[real_dname]
                if issubclass(inst_dclass, dclass):
                    setattr(self, dname, dev)
            else:
                raise MissingDeviceError("Device requirements for this spyrelets ({}) was not met.  Misssing: {}".format(self.name, dname))
        
        for sname, sclass in self.REQUIRED_SPYRELETS.items():
            if sname in spyrelets and isinstance(spyrelets[sname], sclass):
                setattr(self, sname, spyrelets[sname])
            else:
                raise MissingSpyreletError("Sub-Spyrelet requirements for this spyrelets ({}) was not met.  Misssing: {}".format(self.name, sname))

    
    def set_defaults(self, **params_dict):
        d = {'defaults.{}'.format(key):val for key,val in custom_encode(params_dict).items()}
        if len(d):
            return self.client['Spyre_Live_Data']['Register'].update_one({'_id':self.name},{'$set':d}, upsert=True)

    def run(self, *args, **kwargs):
        self.progress = kwargs.pop('progress') if ('progress' in kwargs) else tqdm
        clear_data = kwargs.pop('clear_data') if ('clear_data' in kwargs) else True
        if self.progress is None: self.progress = lambda *args, **kwargs: tqdm(*args, leave=False, **kwargs)
        try:
            args, kwargs = self.enforce_args_units(*args, **kwargs)
            self._stop_flag = False
            if clear_data:
                self.clear_data()
            self.initialize(*args, **kwargs)
            self.main(*args, **kwargs)
        except StopRunning:
            print('stopping spyrelet')
            pass
        except:
            traceback.print_exc()
        finally:
            self.finalize(*args, **kwargs)

    def bg_run(self, *args, **kwargs):
        t = threading.Thread(target=lambda: self.run(*args, **kwargs))
        t.start()
        return t

    def enforce_args_units(self, *args, **kwargs):
        args = list(args)
        def _enforce_units(val, param):
            if 'units' in param:
                if type(val) is Q_:
                    return val.to(param['units'])
                else:
                    return val*Q_(1, param['units'])
            else:
                return val

        sig = inspect.signature(self.main)
        params = list(sig.parameters.keys())
        for name in list(self.PARAMS.keys()):
            param_index = params.index(name)
            if param_index >= len(args):
                if name in kwargs:
                    kwargs[name] = _enforce_units(kwargs[name], self.PARAMS[name])
                else:
                    kwargs[name] = _enforce_units(sig.parameters[name].default, self.PARAMS[name])
            else:
                args[param_index] = _enforce_units(args[param_index], self.PARAMS[name])
        return args, kwargs

    def main(self, *args, **kwargs):
        """This is the method that will contain the user main logic. \
        Should be overwritten"""
        raise NotImplementedError

    def initialize(self, *args, **kwargs):
        """This is the method that will contain the user initialize logic. \
        Should be overwritten"""
        pass

    def finalize(self, *args, **kwargs):
        """This is the method that will contain the user finalize logic. \
        Should be overwritten. This will run even if the initialize or main \
        errors out.
        """
        pass

    def call(self, spyrelet, *args, **kwargs):
        """This is the proper way to call a sub spyrelet. It will take care of \
        keeping the data and calling the proper progress bar. If use_defaults \
        is True (defaults to True) every argument needs to be passed as a \
        keyword argument (ie *args will be ignored).
        """
        keep_data = kwargs.pop('keep_data') if 'keep_data' in kwargs else True
        # use_defaults = kwargs.pop('use_defaults') if 'use_defaults' in kwargs else True
        ignore_child_progress = kwargs.pop('ignore_child_progress') if 'ignore_child_progress' in kwargs else False

        if ignore_child_progress:
            progress = lambda x: x
        else:
            progress = self.progress

        # if not use_defaults:
        spyrelet.run(*args, progress=progress, **kwargs)
        # else:
        #     launcher = Spyrelet_Launcher(spyrelet)
        #     launcher.run(progress=self.progress,**kwargs)
        
        if keep_data:
            if not spyrelet.name in self._child_data:
                self._child_data[spyrelet.name] = list()
            self._child_data[spyrelet.name].append(spyrelet.data)


    def stop(self):
        self._stop_flag = True
        for sname in self.REQUIRED_SPYRELETS:
            getattr(self, sname).stop()

    def clear_data(self):
        self.col.drop()
        self._data = list()
        self._child_data = dict()

    CASTING_DICT = {np.int32:int, np.float64:float}
    def acquire(self, row):
        # Cleanup row
        # Here we will keep numpy arrays as is for local copy, but change it to list for MongoDB
        if not row is None:
            restore_row = dict()
            for k, val in row.items():
                if type(val) == Q_:
                    base_unit = '*'.join('{} ** {}'.format(u, p) for u, p in infer_base_unit(val).items())
                    row[k] = row[k].to(Q_(base_unit)).m
                if type(val) == np.ndarray:
                    restore_row[k] = row[k]
                    row[k] = row[k].tolist()
                if type(val) in self.CASTING_DICT:
                    row[k] = self.CASTING_DICT[type(val)](row[k])

            self.col.insert_one(row)

            for k, val in restore_row.items():
                row[k] = val
            self._data.append(row)
        if self._stop_flag:
            raise StopRunning

    """
    The cache allows for passing information from the spyrelet to remote monitoring processes.
    This cache is meant to be temporary, so unlike data which simply accumulates, this can be overwritten asynchronously
    """
    def reg_cache_clear(self):
        self.client['Spyre_Live_Data']['Register'].update_one({'_id':self.name},{'$set':{'cache':{}}}, upsert=True)

    def reg_cache_store(self, **kwargs):
        d = {'cache.{}'.format(key):val for key,val in custom_encode(kwargs).items()}
        if len(d):
            return self.client['Spyre_Live_Data']['Register'].update_one({'_id':self.name},{'$set':d}, upsert=True)

    def reg_cache_get(self):
        ans = self.client['Spyre_Live_Data']['Register'].find_one({'_id':self.name},{'_id':False, 'cache':True})
        return custom_decode(ans['cache']) if 'cache' in ans else {}
            
    @property
    def child_data(self):
        return self._child_data

    @property
    def data(self):
        return pd.DataFrame(self._data)

    def save(self, filename, **kwargs):
        return save_data(self, filename, **kwargs)

    def validate(self):
        # Check that the signature for main, initialize and finalize functions are the same or not defined
        init_s = inspect.signature(self.initialize)
        fina_s = inspect.signature(self.finalize)
        main_s = inspect.signature(self.main)

        for k,p in main_s.parameters.items():
            if not p.kind in [inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.VAR_KEYWORD]:
                raise Exception('Invalid main signature, Spyrelets do not support positional only, keyword only or var_positional arguments')

        is_default = lambda sig: list(sig.parameters.keys()) == ['args', 'kwargs'] and \
                                 sig.parameters['args'].kind == inspect.Parameter.VAR_POSITIONAL and \
                                 sig.parameters['kwargs'].kind == inspect.Parameter.VAR_KEYWORD
        
        is_equal = lambda s1, s2: list(s1.parameters.keys()) == list(s2.parameters.keys()) and \
                                  all([s1.parameters[x].kind == s2.parameters[x].kind for x in s1.parameters.keys()])

        valid_init = is_default(init_s) or is_equal(init_s, main_s)
        valid_fina = is_default(fina_s) or is_equal(fina_s, main_s)

        if not (valid_fina and valid_init):
            raise Exception('Signature of initialize and finalize function must be the same as that of main for spyrelet: ' + self.name)

class Spyrelet_Launcher():
    def __init__(self, spyrelet):
        self.spyrelet = spyrelet
        params = spyrelet.PARAMS

        ps = inspect.signature(self.spyrelet.main).parameters
        for k, p in ps.items():
            if p.default == inspect.Parameter.empty and not k in params:
                raise Exception("Missing positional argument in PARAMS ({})".format(k))
        
        #First add all the params which require ordering
        def infer(default):
            return {'type':type(default)}
        self.params = OrderedDict([(k, params[k] if k in params else infer(p.default)) for k,p in ps.items() if not p.kind is inspect.Parameter.VAR_KEYWORD])
        for pname, pdescr in self.params.items():
            if not 'defaults' in pdescr and ps[pname].default != inspect._empty:
                self.params[pname].update(default=ps[pname].default)

        self.pos_or_kw_params = list(self.params.keys())
        #Add in all the other params
        for k, val in params.items():
            if not k in self.params:
                self.params[k] = val

        #Load defaults from client
        self.reg = self.spyrelet.client['Spyre_Live_Data']['Register']

    def get_defaults(self):
        ans = self.reg.find_one({'_id':self.spyrelet.name},{'_id':False, 'defaults':True})
        return custom_decode(ans['defaults']) if 'defaults' in ans else {}

    def run(self, progress=None, **params_dict):
        self.spyrelet.set_defaults(**params_dict)
        defaults = self.get_defaults()
        defaults.update(params_dict)
        params = {k:(val.array if type(val)==RangeDict else val) for k, val in defaults.items()}
        pos_or_kw_params = [params[k] for k in self.pos_or_kw_params]
        others = {k:val for k, val in params.items() if not k in self.pos_or_kw_params}
        return self.spyrelet.run(*pos_or_kw_params, progress=progress, **others)
