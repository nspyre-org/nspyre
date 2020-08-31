"""
    nspyre.spyrelet.spyrelet.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    This module defines the base functionality of spyrelets, which are scripts
    that encode the experimental logic.

    Author: Alexandre Bourassa
    Date: 10/30/2019
    Modified: Jacob Feder 7/11/2020
"""

###########################
# imports
###########################

# std
import threading
from collections import OrderedDict
import traceback
import inspect
from copy import copy
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys
from importlib import import_module
import logging

# 3rd party
import pymongo
import pandas as pd
import numpy as np
from pint.util import infer_base_unit
from tqdm.auto import tqdm

# nspyre
from nspyre.gui.data_handling import save_data
from nspyre.config.config_files import load_config, get_config_param, \
                                    ConfigEntryNotFoundError
from nspyre.utils.misc import get_mongo_client, custom_decode, custom_encode, \
                                RangeDict
from nspyre.definitions import Q_

###########################
# globals
###########################

# config file key for spyrelets
CONFIG_SPYRELETS_KEY = 'spyrelets'
# config file key for the python file of the spyrelet
CONFIG_SPYRELETS_FILE_KEY = 'file'
# config file key for the class of the spyrelet
CONFIG_SPYRELETS_CLASS_KEY = 'class'
# config file key for the device aliases of a spyrelet
CONFIG_DEVS_KEY = 'device_aliases'
# config file key for the sub-spyrelets of a spyrelet
CONFIG_SUB_SPYRELETS_KEY = 'spyrelets'
# config file key for spyrelet arguments
CONFIG_SPYRELETS_ARGS_KEY = 'args'

###########################
# exceptions
###########################

class StopRunning(Exception):
    pass

class SpyreletLoadError(Exception):
    """Exception while loading a Spyrelet"""
    def __init__(self, error, msg):
        super().__init__(msg)
        if error:
            logging.exception(error)

###########################
# classes / functions
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

    def __init__(self, unique_name, manager, device_aliases={}, spyrelets={},
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
            'class': 'unused' #"{}.{}".format(self.__class__.__module__, self.__class__.__name__),
        }

        self.client = get_mongo_client(mongodb_addr)
        self.col = self.client['Spyre_Live_Data'][unique_name]
        self.client['Spyre_Live_Data']['Register'].update_one({'_id':unique_name},{'$set':reg_entry}, upsert=True)
        self.clear_data()
        
        # check that the server devices are accessible and add them as
        # instance variables
        for dev_alias in self.REQUIRED_DEVICES:
            try:
                dev_accessor = device_aliases[dev_alias]
            except Exception as exc:
                raise SpyreletLoadError(exc, 'Spyrelet [{}] requires the '
                        'device [{}] but it wasn\'t defined in the [{}] '
                        'section of the config file'.format(unique_name, \
                            dev_alias, CONFIG_DEVS_KEY)) from None
            if dev_accessor in manager.devs:
                setattr(self, dev_alias, manager.devs[dev_accessor])
            else:
                raise SpyreletLoadError(None, 'Spyrelet [{}] requires the '
                        'device [{}] (alias [{}]) but either the instrument '
                        'server is unreachable, or the device isn\'t available '
                        'on the server'.\
                        format(unique_name, dev_accessor, dev_alias))

        # check that the sub spyrelets are loaded and add them as
        # instance variables
        for sname, sclass in self.REQUIRED_SPYRELETS.items():
            if sname in spyrelets and isinstance(spyrelets[sname], sclass):
                setattr(self, sname, spyrelets[sname])
            else:
                raise SpyreletLoadError('Spyrelet [{}] requires the '
                        'sub-spyrelet [{}] but it wasn\'t loaded'.\
                        format(unique_name, sname))

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

        is_default = lambda sig: list(sig.parameters.keys()) == [CONFIG_SPYRELETS_ARGS_KEY, 'kwargs'] and \
                                 sig.parameters[CONFIG_SPYRELETS_ARGS_KEY].kind == inspect.Parameter.VAR_POSITIONAL and \
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

def load_spyrelet_class(spyrelet_name, cfg):
    """Load a spyrelet class from a file (whose location is defined in cfg)"""
    # discover spyrelet file and class
    spyrelet_path_str,_ = get_config_param(cfg, [CONFIG_SPYRELETS_KEY , \
                                spyrelet_name, CONFIG_SPYRELETS_FILE_KEY])
    spyrelet_class_name, spyrelet_cfg_path_str = get_config_param(cfg, \
                                [CONFIG_SPYRELETS_KEY, spyrelet_name, \
                                CONFIG_SPYRELETS_CLASS_KEY])
    # resolve the spyrelet file location
    # if the path isn't absolute resolve it relative to the config file
    spyrelet_path = Path(spyrelet_path_str)
    if not spyrelet_path.is_absolute():
        spyrelet_path = (Path(spyrelet_cfg_path_str).parent / \
                                spyrelet_path).resolve()
    spyrelet_dir = spyrelet_path.parent
    spyrelet_file_name = str(spyrelet_path.name)
    # remove .py extension
    spyrelet_file_name = spyrelet_file_name.split('.py')[0]
    # load the spyrelet class from its python file
    sys.path.append(str(spyrelet_dir))
    spyrelet_module = import_module(spyrelet_file_name)
    spyrelet_class = getattr(spyrelet_module, spyrelet_class_name)
    return spyrelet_class

def load_all_spyrelets(manager, filepath=None):
    """Load all of the spyrelets from the config file"""
    cfg = load_config(filepath)
    # spyrelet parameters to parse
    spyrelet_configs,_ = copy(get_config_param(cfg, [CONFIG_SPYRELETS_KEY]))
    # loaded spyrelets
    loaded_spyrelets = {}
    
    # recursive function that loads a spyrelet from the config
    # and also loads all sub-spyrelets
    def load_spyrelet(spyrelet_name):
        if spyrelet_name in loaded_spyrelets:
            raise SpyreletLoadError(None, 'spyrelet [{}] is already '
                                        'defined'.format(spyrelet_name))
        
        # discover any sub-spyrelets
        try:
            sub_spyrelet_names,_ = get_config_param(cfg, \
                                        [CONFIG_SPYRELETS_KEY, spyrelet_name, \
                                        CONFIG_SUB_SPYRELETS_KEY])
        except ConfigEntryNotFoundError:
            logging.debug('spyrelet [{}] no sub-spyrelets found'.\
                            format(spyrelet_name))
            sub_spyrelet_names = {}
        
        # iterate through the sub-spyrelets and load them
        sub_spyrelets = {}
        for s in sub_spyrelet_names:
            if s in loaded_spyrelets:
                sub_spyrelets[s] = loaded_spyrelets[s]
            else:
                try:
                    sub_spyrelets[s] = load_spyrelet(s)
                except:
                    raise SpyreletLoadError(None, 'spyrelet [{}] '
                                        'sub-spyrelet [{}] failed to load'.\
                                        format(spyrelet_name, s))
        
        # discover and load the spyrelet class
        spyrelet_class = load_spyrelet_class(spyrelet_name, cfg)

        # discover the spyrelet devices
        try:
            dev_aliases,_ = get_config_param(cfg, [CONFIG_SPYRELETS_KEY, \
                                spyrelet_name, CONFIG_DEVS_KEY])
        except ConfigEntryNotFoundError:
            logging.debug('spyrelet [{}] no device aliases found'.\
                            format(spyrelet_name))
            dev_aliases = {}
        
        # discover the spyrelet arguments
        try:
            args,_ = get_config_param(cfg, [CONFIG_SPYRELETS_KEY, \
                                spyrelet_name, CONFIG_SPYRELETS_ARGS_KEY])
        except ConfigEntryNotFoundError:
            logging.debug('spyrelet [{}] no args found'.format(spyrelet_name))
            args = {}
        args = custom_decode(args)
        
        # create the spyrelet
        spyrelet = spyrelet_class(spyrelet_name, manager, \
                                device_aliases=dev_aliases, \
                                spyrelets=sub_spyrelets, **args)
        loaded_spyrelets[spyrelet_name] = spyrelet
        logging.info('loaded spyrelet [{}]'.format(spyrelet_name))

        # remove this spyrelet from the list of spyrelets to be loaded
        del spyrelet_configs[spyrelet_name]
        return spyrelet

    # parse the spyrelets, loading them as we go until there
    # are none left
    while bool(spyrelet_configs):
        load_spyrelet(next(iter(spyrelet_configs)))
    return loaded_spyrelets

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