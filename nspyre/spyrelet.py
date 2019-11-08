import pymongo
from nspyre.instrument_manager import Instrument_Manager
from nspyre.utils import connect_to_master
# from instrument_server import Remote_Device
import pandas as pd
import numpy as np

from lantz import Q_
from pint.util import infer_base_unit
import traceback
import inspect
from importlib import import_module
from collections import OrderedDict

class MissingDeviceError(Exception):
    pass

class MissingSpyreletError(Exception):
    pass

class Spyrelet():
    REQUIRED_DEVICES = dict()
    REQUIRED_SPYRELETS = dict()
    LAUNCHER_PARAMS = list()

    """
    A few notes about the spyrelet class:
        - This is the class you need to subclass for making experiments.

        - All devices used in the spyrelet must be listed in the REQURIRED_DEVICES dict
        - All sub-spyrelet must also be listed in the REQUIRED_SPYRELETS dict
        - Upon instanciation the class will check the __init__ arguments devices and spyrelets to make sure they satisfy these requirements

        - For higher performance we will store the data internally as a list instead of a dataframe.  Quicker to append to a list.

    """
    def __init__(self, unique_name, mongodb_addrs, manager, spyrelets={}):
        self.name = unique_name
        self.mongodb_addrs = mongodb_addrs
        self.validate()
        
        reg_entry = {
            '_id':unique_name,
            'class':"{}.{}".format(self.__class__.__module__, self.__class__.__name__),
        }

        client = connect_to_master(mongodb_addrs)
        self.col = client['Spyre_Live_Data'][unique_name]
        client['Spyre_Live_Data']['Register'].update_one({'_id':unique_name},{'$set':reg_entry}, upsert=True)
        self.clear_data()

        # This is imported here otherwise the import may occur before the Remote_Device_Instance is dynamically generated...
        # from instrument_server import Remote_Device

        devices = manager.get_devices()
        for dname, dclass in self.REQUIRED_DEVICES.items():
            if dname in devices:
                # isRemoteDevice = issubclass(type(devices[dname]), Remote_Device)
                #This is a convoluted way of checking subclass
                isRemoteDevice = any(['spyre.instrument_server.Remote_Device' in str(c) for c in inspect.getmro(type(devices[dname]))])

                if isRemoteDevice :
                    class_name = devices[dname].info['class'].split('.')[-1]
                    mod = import_module(devices[dname].info['class'].replace('.'+class_name, ''))
                    inst_dclass = getattr(mod, class_name)
                    dev = devices[dname]
                else:
                    inst_dclass = type(devices[dname])
                    dev = devices[dname]
                if issubclass(inst_dclass, dclass):
                    setattr(self, dname, dev)
            else:
                raise MissingDeviceError("Device requirements for this spyrelets ({}) was not met.  Misssing: {}".format(self.name, dname))
        
        for sname, sclass in self.REQUIRED_SPYRELETS.items():
            if sname in spyrelets and isinstance(spyrelets[sname], sclass):
                setattr(self, sname, spyrelets[sname])
            else:
                raise MissingSpyreletError("Sub-Spyrelet requirements for this spyrelets ({}) was not met.  Misssing: {}".format(self.name, sname))

    
    def run(self, *args, **kwargs):
        try:
            self.clear_data()
            self.initialize(*args, **kwargs)
            self.main(*args, **kwargs)
        except:
            traceback.print_exc()
        finally:
            self.finalize(*args, **kwargs)

    def main(self, *args, **kwargs):
        """This is the method that will contain the user main logic.  Should be overwritten"""
        raise NotImplementedError

    def initialize(self, *args, **kwargs):
        """This is the method that will contain the user initialize logic.  Should be overwritten"""
        pass

    def finalize(self, *args, **kwargs):
        """This is the method that will contain the user finalize logic. Should be overwritten
        This will run even if the initialize or main errors out
        """
        pass
        
    def clear_data(self):
        self.col.drop()
        self._data = list()

    def acquire(self, row):
        # Cleanup row
        # Here we will keep numpy arrays as is for local copy, but change it to list for MongoDB
        restore_row = dict()
        for k, val in row.items():
            if type(val) == Q_:
                base_unit = '*'.join('{} ** {}'.format(u, p) for u, p in infer_base_unit(val).items())
                row[k] = row[k].to(Q_(base_unit)).m
            if type(val) == np.ndarray:
                restore_row[k] = row[k]
                row[k] = row[k].tolist()
        self.col.insert_one(row)

        for k, val in restore_row.items():
            row[k] = val
        self._data.append(row)
            

    @property
    def data(self):
        return pd.DataFrame(self._data)

    def validate(self):
        # Check that the signature for main, initialize and finalize functions are the same or not defined
        init_s = inspect.signature(self.initialize)
        fina_s = inspect.signature(self.finalize)
        main_s = inspect.signature(self.main)

        for k,p in main_s.parameters.items():
            if not p.kind in [inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.VAR_KEYWORD]:
                raise('Invalid main signature, Spyrelets do not support positional only, keyword only or var_positional arguments')

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
        params = spyrelet.LAUNCHER_PARAMS

        ps = inspect.signature(self.spyrelet.main).parameters
        for k, p in ps.items():
            if p.default == inspect.Parameter.empty and not k in params:
                raise Exception("Missing positional argument in LAUNCHER_PARAMS ({})".format(k))
        
        #First add all the params which require ordering
        self.params = OrderedDict([(k, params[k]) for k,p in ps.items() if not p.kind is inspect.Parameter.VAR_KEYWORD])
        self.pos_or_kw_params = list(self.params.keys())
        #Add in all the other params
        for k, val in params.items():
            if not k in self.params:
                self.params[k] = val

    def run(self, params_dict):
        pos_or_kw_params = [self.params[k] for k in self.pos_or_kw_params]
        others = {k:val for k, val in self.params.items() if not k in self.pos_or_kw_params}
        return self.spyrelet.run(*pos_or_kw_params, **others)
        
        
            