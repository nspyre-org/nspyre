"""The base class for spyrelets and associated utility functions.

The Spyrelet class is the base class for writing experimentation logic. These
can be as simple or complex as desired and need to be Leave one blank line.  The rest of this docstring should contain an
overall description of the module or program.  Optionally, it may also
contain a brief description of exported classes and functions and/or usage
examples.

  Typical usage example:

  foo = ClassFoo()
  bar = foo.FunctionBar()

Copyright (c) 2020, Alexandre Bourassa, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from collections import OrderedDict
import copy
import inspect
import logging
import pathlib
import threading
import traceback

import numpy as np
import pandas as pd
from pint.util import infer_base_unit
from pymongo.errors import PyMongoError
from tqdm.auto import tqdm

from nspyre.config.config_files import get_config_param
from nspyre.definitions import Q_
from nspyre.errors import EntryNotFoundError, SpyreletLoadError, SpyreletRunningError, SpyreletUnloadError
from nspyre.gui.data_handling import save_data
from nspyre.misc.misc import custom_decode, custom_encode, get_mongo_client, load_class_from_file, RangeDict

logger = logging.getLogger(__name__)

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
# config file key for spyrelet keyword arguments
CONFIG_SPYRELETS_KWARGS_KEY = 'kwargs'
# record of the loaded spyrelets
_LOADED_SPYRELETS = {}


class Spyrelet:
    """The base class for constructing experiment logic.

    This is the class you need to subclass for making experiments.
    All devices used in the spyrelet must be listed in the
            REQUIRED_DEVICES dict
    All sub-spyrelets must also be listed in the REQUIRED_SPYRELETS dict
    Upon instantiation the class will check the __init__ arguments
            devices and spyrelets to make sure they satisfy these requirements
    For higher performance we will store the data internally as a list
            instead of a dataframe.  Quicker to append to a list.

    Attributes:
        REQUIRED_DEVICES: A dict with the names and associated class of the required devices.
        REQUIRED_SPYRELETS: A dict with the name and associated class of the required sub-spyrelet(s).
        PARAMS: A definition of the parameters that are used as arguments to the main/initialize/finalize functions.
                These are used both to generate a launcher GUI and to enforce units at call time.
        CONSTS: An extra dictionary, which can be defined by the user at initialization time.
    """

    REQUIRED_DEVICES = list()
    REQUIRED_SPYRELETS = dict()
    PARAMS = dict()
    CONSTS = dict()

    def __init__(self, unique_name='', gateway=None, device_aliases={}, spyrelets={}, mongodb_addr=None, **consts):
        self.name = unique_name
        self.progress = tqdm
        self.spyrelets = spyrelets
        self.CONSTS = self.CONSTS.copy()
        self.CONSTS.update(**consts)
        self.last_kwargs = dict()

        self.mongodb_addr = mongodb_addr
        self.validate()
        
        reg_entry = {
            '_id': unique_name,
            'class': 'unused'  # "{}.{}".format(self.__class__.__module__, self.__class__.__name__),
        }

        self.client = get_mongo_client(mongodb_addr)
        self.col = self.client['Spyre_Live_Data'][unique_name]
        self.client['Spyre_Live_Data']['Register'].update_one({'_id': unique_name}, {'$set': reg_entry}, upsert=True)
        self.clear_data()
        
        # check that the server devices are accessible and add them as
        # instance variables
        for dev_alias in self.REQUIRED_DEVICES:
            try:
                # e.g. "local1/dev1"
                dev_accessor = device_aliases[dev_alias]
            except Exception as exc:
                raise SpyreletLoadError(exc, 'Spyrelet [{}] requires the '
                                             'device [{}] but it wasn\'t defined in the [{}] '
                                             'section of the config file'.format(unique_name, dev_alias, CONFIG_DEVS_KEY)) from None
            try:
                server_name, device_name = device_aliases[dev_alias].split('/')
            except:
                raise SpyreletLoadError(None, 'Spyrelet [{}] with the '
                                              'device alias [{}] has an invalid device accessor [{}].'
                                              'The accessor should be in the form '
                                              '"server_name/device_name"'.format(unique_name, dev_accessor, dev_alias))
            try:
                server = getattr(gateway, server_name)
            except:
                raise SpyreletLoadError(None, 'Spyrelet [{}] requires the '
                                              'device [{}] (alias [{}]) but the instrument '
                                              'server is unreachable'.format(unique_name, dev_accessor, dev_alias))
            try:
                device = getattr(server, device_name)
            except:
                raise SpyreletLoadError(None, 'Spyrelet [{}] requires the '
                                              'device [{}] (alias [{}]) but the instrument '
                                              'server doesn\'t contain the device'.format(unique_name, dev_accessor,
                                                                                          dev_alias))
            setattr(self, dev_alias, device)

        # check that the sub spyrelets are loaded and add them as
        # instance variables
        for sname, sclass in self.REQUIRED_SPYRELETS.items():
            if sname in spyrelets:# and isinstance(spyrelets[sname], sclass):
                setattr(self, sname, spyrelets[sname])
            else:
                raise SpyreletLoadError('Spyrelet [{}] requires the sub-spyrelet [{}] but it wasn\'t loaded'.format(unique_name, sname))

    def set_defaults(self, **params_dict):
        d = {'defaults.{}'.format(key): val for key, val in custom_encode(params_dict).items()}
        if len(d):
            return self.client['Spyre_Live_Data']['Register'].update_one({'_id': self.name}, {'$set': d}, upsert=True)

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
        except SpyreletRunningError:
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
                    return val * Q_(1, param['units'])
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
        #     launcher = SpyreletLauncher(spyrelet)
        #     launcher.run(progress=self.progress,**kwargs)
        
        if keep_data:
            if spyrelet.name not in self._child_data:
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

    CASTING_DICT = {np.int32: int, np.float64: float}

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
            raise SpyreletRunningError

    """
    The cache allows for passing information from the spyrelet to remote monitoring processes.
    This cache is meant to be temporary, so unlike data which simply accumulates, this can be overwritten asynchronously
    """

    def reg_cache_clear(self):
        self.client['Spyre_Live_Data']['Register'].update_one({'_id': self.name}, {'$set': {'cache': {}}}, upsert=True)

    def reg_cache_store(self, **kwargs):
        d = {'cache.{}'.format(key): val for key, val in custom_encode(kwargs).items()}
        if len(d):
            return self.client['Spyre_Live_Data']['Register'].update_one({'_id': self.name}, {'$set': d}, upsert=True)

    def reg_cache_get(self):
        ans = self.client['Spyre_Live_Data']['Register'].find_one({'_id': self.name}, {'_id': False, 'cache': True})
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

        for k, p in main_s.parameters.items():
            if p.kind not in [inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.VAR_KEYWORD]:
                raise Exception('Invalid main signature, Spyrelets do not support positional only, keyword only or var_positional arguments')

        is_default = lambda sig: list(sig.parameters.keys()) == [CONFIG_SPYRELETS_ARGS_KEY, 'kwargs'] and sig.parameters[CONFIG_SPYRELETS_ARGS_KEY].kind == inspect.Parameter.VAR_POSITIONAL and sig.parameters['kwargs'].kind == inspect.Parameter.VAR_KEYWORD

        is_equal = lambda s1, s2: list(s1.parameters.keys()) == list(s2.parameters.keys()) and all([s1.parameters[x].kind == s2.parameters[x].kind for x in s1.parameters.keys()])

        valid_init = is_default(init_s) or is_equal(init_s, main_s)
        valid_fina = is_default(fina_s) or is_equal(fina_s, main_s)

        if not (valid_fina and valid_init):
            raise Exception('Signature of initialize and finalize function must be the same as that of main for spyrelet: ' + self.name)


class SpyreletLauncher:
    def __init__(self, spyrelet):
        self.spyrelet = spyrelet
        params = spyrelet.PARAMS

        ps = inspect.signature(self.spyrelet.main).parameters
        for k, p in ps.items():
            if p.default == inspect.Parameter.empty and not k in params:
                raise Exception("Missing positional argument in PARAMS ({})".format(k))

        # First add all the params which require ordering
        def infer(default):
            return {'type': type(default)}

        self.params = OrderedDict([(k, params[k] if k in params else infer(p.default)) for k, p in ps.items() if p.kind is not inspect.Parameter.VAR_KEYWORD])
        for pname, pdescr in self.params.items():
            if not 'defaults' in pdescr and ps[pname].default != inspect._empty:
                self.params[pname].update(default=ps[pname].default)

        self.pos_or_kw_params = list(self.params.keys())
        # Add in all the other params
        for k, val in params.items():
            if not k in self.params:
                self.params[k] = val

        # Load defaults from client
        self.reg = self.spyrelet.client['Spyre_Live_Data']['Register']

    def get_defaults(self):
        ans = self.reg.find_one({'_id': self.spyrelet.name}, {'_id': False, 'defaults': True})
        return custom_decode(ans['defaults']) if 'defaults' in ans else {}

    def run(self, progress=None, **params_dict):
        self.spyrelet.set_defaults(**params_dict)
        defaults = self.get_defaults()
        defaults.update(params_dict)
        params = {k: (val.array if type(val) == RangeDict else val) for k, val in defaults.items()}
        pos_or_kw_params = [params[k] for k in self.pos_or_kw_params]
        others = {k: val for k, val in params.items() if not k in self.pos_or_kw_params}
        return self.spyrelet.run(*pos_or_kw_params, progress=progress, **others)


def load_spyrelet_class(spyrelet_name, cfg):
    """Load a spyrelet class from a file (whose location is defined in cfg)"""
    # discover spyrelet file and class
    spyrelet_path_str, _ = get_config_param(cfg, [CONFIG_SPYRELETS_KEY, spyrelet_name, CONFIG_SPYRELETS_FILE_KEY])
    spyrelet_class_name, spyrelet_cfg_path_str = get_config_param(cfg, [CONFIG_SPYRELETS_KEY, spyrelet_name, CONFIG_SPYRELETS_CLASS_KEY])
    # resolve the spyrelet file location
    # if the path isn't absolute resolve it relative to the config file
    spyrelet_path = pathlib.Path(spyrelet_path_str)
    if not spyrelet_path.is_absolute():
        spyrelet_path = pathlib.Path(spyrelet_cfg_path_str).parent / spyrelet_path
    spyrelet_path = spyrelet_path.resolve()

    if not spyrelet_path.is_file():
        raise SpyreletLoadError(None, f'spyrelet [{spyrelet_name}] file [{spyrelet_path}] doesn\'t exist')

    return load_class_from_file(spyrelet_path, spyrelet_class_name)


def load_spyrelet(spyrelet_name, gateway, sub_spyrelet=False):
    """
    recursive function that loads a spyrelet from the config
    and also loads all sub-spyrelets
    """
    cfg = gateway.config
    if spyrelet_name in _LOADED_SPYRELETS:
        if sub_spyrelet:
            return
        else:
            raise SpyreletLoadError(None, 'spyrelet [{}] is already '
                                          'defined'.format(spyrelet_name))

    # discover any sub-spyrelets
    try:
        sub_spyrelet_names, _ = get_config_param(cfg, [CONFIG_SPYRELETS_KEY, spyrelet_name, CONFIG_SUB_SPYRELETS_KEY])
    except EntryNotFoundError:
        logger.debug('spyrelet [{}] no sub-spyrelets found'.format(spyrelet_name))
        sub_spyrelet_names = {}

    # iterate through the sub-spyrelets and load them
    sub_spyrelets = {}
    for s in sub_spyrelet_names:
        if s in _LOADED_SPYRELETS:
            sub_spyrelets[s] = _LOADED_SPYRELETS[s]
        else:
            try:
                sub_spyrelets[s] = load_spyrelet(s, gateway, sub_spyrelet=True)
            except:
                raise SpyreletLoadError(None, 'spyrelet [{}] sub-spyrelet [{}] failed to load'.format(spyrelet_name, s))

    # discover and load the spyrelet class
    spyrelet_class = load_spyrelet_class(spyrelet_name, cfg)

    # discover the spyrelet devices
    try:
        dev_aliases, _ = get_config_param(cfg, [CONFIG_SPYRELETS_KEY, \
                                                spyrelet_name, CONFIG_DEVS_KEY])
    except EntryNotFoundError:
        logger.debug('spyrelet [{}] no device aliases found'. \
                      format(spyrelet_name))
        dev_aliases = {}

    # discover the spyrelet arguments
    try:
        args, _ = get_config_param(cfg, [CONFIG_SPYRELETS_KEY, \
                                         spyrelet_name, CONFIG_SPYRELETS_ARGS_KEY])
    except EntryNotFoundError:
        logger.debug('spyrelet [{}] no args found'.format(spyrelet_name))
        args = []
    args = custom_decode(args)

    # discover the spyrelet keyword arguments
    try:
        kwargs, _ = get_config_param(cfg, [CONFIG_SPYRELETS_KEY, \
                                         spyrelet_name, CONFIG_SPYRELETS_KWARGS_KEY])
    except EntryNotFoundError:
        logger.debug('spyrelet [{}] no kwargs found'.format(spyrelet_name))
        kwargs = {}
    kwargs = custom_decode(kwargs)

    # create the spyrelet
    spyrelet = spyrelet_class(*args, spyrelet_name, gateway, **kwargs, device_aliases=dev_aliases, spyrelets=sub_spyrelets)
    _LOADED_SPYRELETS[spyrelet_name] = spyrelet
    logger.info('loaded spyrelet [{}]'.format(spyrelet_name))

    return spyrelet


def load_all_spyrelets(gateway):
    """Load all of the spyrelets from the configuration file.

    Instantiates the spyrelet classes retrieved from the given classes specified in the active
    configuration file. An InservGateway instance must be passed for handling the connection to
    the devices specificed in each spyrelet.

    Args:
        manager: An InservGateway instance connected to a running InstrumentServer.
        filepath: Optional; An absolute filepath to a configuration file. If a filepath is specified,
            the spyrelets will be loaded from this file. Otherwise, the default behavior is to load
            from the active configuration file.

    Returns:
        A dict mapping keys of spyrelet names to the corresponding instance of that spyrelet class.

    Raises:
        SpyreletLoadError: An error occurred because one (or more) spyrelet(s) is(are) already loaded.
    """
    # spyrelet parameters to parse
    spyrelet_configs, _ = copy.copy(get_config_param(gateway.config, [CONFIG_SPYRELETS_KEY]))
    # check to see if any spyrelets are loaded
    if _LOADED_SPYRELETS:
        raise SpyreletLoadError(None, 'the following spyrelets were already loaded so nothing was done: {}'.format(_LOADED_SPYRELETS))

    # parse the spyrelets, loading them as we go until there
    # are none left
    while bool(spyrelet_configs):
        spyrelet_name = next(iter(spyrelet_configs))
        load_spyrelet(spyrelet_name, gateway)
        # remove this spyrelet from the list of spyrelets to be loaded
        del spyrelet_configs[spyrelet_name]
    return _LOADED_SPYRELETS


def unload_spyrelet(name, client=None):
    """function to unload a current spyrelet"""
    if name not in _LOADED_SPYRELETS:
        raise SpyreletUnloadError(None, 'the spyrelet {} does not exist'.format(name))
    if client is None:
        client = get_mongo_client()
    try:
        client['Spyre_Live_Data'][name].drop()
        client['Spyre_Live_Data']['Register'].delete_one({'_id': name})
    except PyMongoError as error:
        raise SpyreletUnloadError(error, 'error attempting to remove spyrelet: {} from the MongoDB server'.format(name))
    _LOADED_SPYRELETS.pop(name)


def unload_all_spyrelets(except_list=[], client=None):
    """function to unload all current spyrelet(s)"""
    if client is None: client = get_mongo_client()
    all_in_reg = [x['_id'] for x in client['Spyre_Live_Data']['Register'].find({}, {})]
    for name in all_in_reg:
        if not name in except_list:
            unload_spyrelet(name, client=client)


def reload_spyrelet(spyrelet_names, gateway, client=None):
    """function to reload current spyrelet(s)"""
    # if only one name is passed, convert it to list for handling
    if type(spyrelet_names) is not list:
        spyrelet_names = [spyrelet_names]

    if client is None:
        client = get_mongo_client()

    for name in spyrelet_names:
        unload_spyrelet(name, client=client)
        load_spyrelet(name, gateway)


def reload_all_spyrelets(gateway, except_list=[], client=None):
    """function to reload all current spyrelet(s)"""
    if client is None:
        client = get_mongo_client()

    # get the symmetric difference
    spyrelets = list(set(_LOADED_SPYRELETS.keys()) ^ set(except_list))

    unload_all_spyrelets(except_list, client)
    if except_list:
        for name in spyrelets:
            load_spyrelet(name, gateway)
    else:
        load_all_spyrelets(gateway)


@property
def LOADED_SPYRELETS():
    """function to return all loaded spyrelets"""
    return _LOADED_SPYRELETS
