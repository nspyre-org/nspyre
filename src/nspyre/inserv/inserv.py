"""
This module:
    - loads the server config file
    - connects to all of the instruments specified in the config files
    - creates a RPyC (python remote procedure call) server to allow remote
        machines to access the instruments (should be done using InservGateway)

Author: Jacob Feder
Date: 7/8/2020
"""

###########################
# imports
###########################

# std
from pathlib import Path
import threading
import time
from functools import partial
import copy
import functools
import logging

# 3rd party
import rpyc
from rpyc.utils.server import ThreadedServer
import pymongo
from lantz import Q_, DictFeat
from pimpmyclass.helpers import DictPropertyNameKey
from pint import Quantity

# nspyre
from nspyre.config.config_files import get_config_param, load_config, \
                                    meta_config_add, meta_config_remove, \
                                    meta_config_files, ConfigEntryNotFoundError
from nspyre.misc.misc import load_class_from_str, load_class_from_file, register_quantity_brining
from nspyre.definitions import MONGO_SERVERS_KEY, \
                MONGO_SERVERS_SETTINGS_KEY, MONGO_CONNECT_TIMEOUT, \
                MONGO_RS, RPYC_SYNC_TIMEOUT, CONFIG_MONGO_ADDR_KEY, \
                join_nspyre_path, SERVER_META_CONFIG_PATH

# for properly serializing/deserializing quantity objects using the local
# pint unit registry
register_quantity_brining(Q_)

###########################
# globals
###########################

logger = logging.getLogger(__name__)

CONFIG_SERVER_DEVICES = 'devices'
CONFIG_SERVER_DEVICE_LANTZ_CLASS = 'lantz_class'
CONFIG_SERVER_DEVICE_CLASS_FILE = 'class_file'
CONFIG_SERVER_DEVICE_CLASS_NAME = 'class'

RPYC_SERVER_STOP_EVENT = threading.Event()

###########################
# exceptions
###########################

class InstrumentServerError(Exception):
    """General InstrumentServer exception"""
    def __init__(self, error, msg):
        super().__init__(msg)
        if error:
            logger.exception(error)

###########################
# classes
###########################


rpyc.core.consts.HANDLE_ABOUT_TO_CLOSE = 21
from rpyc.core.protocol import consts


class InstrumentConnection(rpyc.Connection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _pre_cleanup(self):  # IO
        self._local_root.on_about_to_disconnect(self)

    def close(self, _catchall=True):  # IO
        """closes the connection, releasing all held resources"""
        if self._closed:
            return
        self._closed = True
        try:
            self.sync_request(consts.HANDLE_ABOUT_TO_CLOSE)
            self._async_request(consts.HANDLE_CLOSE)
        except EOFError:
            pass
        except Exception:
            if not _catchall:
                raise
        finally:
            self._cleanup(_anyway=True)

    @classmethod
    def _request_handlers(cls):  # request handlers
        return {
            consts.HANDLE_PING: cls._handle_ping,
            consts.HANDLE_CLOSE: cls._handle_close,
            consts.HANDLE_GETROOT: cls._handle_getroot,
            consts.HANDLE_GETATTR: cls._handle_getattr,
            consts.HANDLE_DELATTR: cls._handle_delattr,
            consts.HANDLE_SETATTR: cls._handle_setattr,
            consts.HANDLE_CALL: cls._handle_call,
            consts.HANDLE_CALLATTR: cls._handle_callattr,
            consts.HANDLE_REPR: cls._handle_repr,
            consts.HANDLE_STR: cls._handle_str,
            consts.HANDLE_CMP: cls._handle_cmp,
            consts.HANDLE_HASH: cls._handle_hash,
            consts.HANDLE_INSTANCECHECK: cls._handle_instancecheck,
            consts.HANDLE_DIR: cls._handle_dir,
            consts.HANDLE_PICKLE: cls._handle_pickle,
            consts.HANDLE_DEL: cls._handle_del,
            consts.HANDLE_INSPECT: cls._handle_inspect,
            consts.HANDLE_BUFFITER: cls._handle_buffiter,
            consts.HANDLE_OLDSLICING: cls._handle_oldslicing,
            consts.HANDLE_CTXEXIT: cls._handle_ctxexit,
            consts.HANDLE_ABOUT_TO_CLOSE: cls._handle_about_to_close,
        }

    def _handle_about_to_close(self):  # request handler
        self._pre_cleanup()


class InstrumentService(rpyc.Service):

    _protocol = InstrumentConnection

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_about_to_disconnect(self, conn):
        """called when the connection had already terminated for cleanup
        (must not perform any IO on the connection)"""
        pass


class VoidInstrumentService(InstrumentService):
    """void service - an do-nothing service"""
    __slots__ = ()


rpyc.Connection = InstrumentConnection
rpyc.Service = InstrumentService
rpyc.VoidService = VoidInstrumentService


class InstrumentServer(InstrumentService):
    """RPyC provider that loads lantz devices and exposes them to the remote
    client
    """

    def __init__(self, config_file=None, mongo_addr=None):
        super().__init__()
        # if the config file isn't specified, get it from the meta-config
        if not config_file:
            config_file = load_meta_config(SERVER_META_CONFIG_PATH)
        # lantz devices
        self._devs = {}
        # configuration
        self.config = {}
        self.config_file = None
        # server settings
        self.port = None
        # rpyc server object
        self._rpyc_server = None
        # mongodb
        self.db_name = None
        self.mongo_addr = None
        self.mongo_client = None
        self.db = None

        # storage container for hook methods that update mongodb feats when
        # lantz feats are changed - this is required because pysignal uses
        # weakrefs, so any local functions you pass to it will fail when they
        # go out of scope
        # TODO replace with partials
        self.feat_hook_functions = {}
        self.dictfeat_hook_functions = {}

        # start everything
        self.reload_config(config_file)
        self.reload_server_config()
        self.connect_mongo(mongo_addr)
        self.reload_devices()
        self.start_server()

    def __getattr__(self, name):
        """Allow the user to access the driver objects directly using
        e.g. inserv.fake_tcpip_sg.amplitude notation
        """
        if name in self._devs:
            return self._devs[name]
        else:
            return self.__getattribute__(name)
            #raise AttributeError('\'{}\' object has no attribute \'{}\''.\
            #            format(self.__class__.__name__, name))

    def on_connect(self, conn):
        """Called when a client connects to the RPyC server"""
        logger.info('client [{}] connected'.format(conn))

    def on_about_to_disconnect(self, conn):
        logger.info('client [{}] about to disconnect'.format(conn))
        for device_name, device in self._devs.items():
            # iterate over all feats and dictfeats
            for attr_name, attr in list(device._lantz_feats.items()) + list(device._lantz_dictfeats.items()):
                if isinstance(attr_name, DictPropertyNameKey):
                    # filter out weird dictfeat feats
                    continue
                # access the PySignal slots
                attr_slots = getattr(device, attr_name + '_changed')._slots
                for slot in attr_slots:
                    if isinstance(slot, functools.partial) and slot.__name__ == 'InstrumentManager_getattr_func':
                        getattr(device, attr_name + '_changed').disconnect(slot)


    def on_disconnect(self, conn):
        """Called when a client disconnects from the RPyC server"""
        logger.info('client [{}] disconnected'.format(conn))

        # when an RPyC client disconnects, there are dangling netrefs
        # left over in PySignal _slots that point to objects on the client
        # side which are now inaccessible
        # this block detects and removes the references by attempting to
        # access them with a try/except
        # TODO this logic should really be implemented in PySignal during emit()
        for device_name, device in self._devs.items():
            # iterate over all feats and dictfeats
            for attr_name, attr in list(device._lantz_feats.items()) + list(device._lantz_dictfeats.items()):
                if isinstance(attr_name, DictPropertyNameKey):
                    # filter out weird dictfeat feats
                    continue
                # access the PySignal slots
                attr_slots = getattr(device, attr_name + '_changed')._slots
                for index, slot in enumerate(attr_slots):
                    try:
                        # trying to compare slot to something will force RPyC
                        # to attempt to retrieve it
                        if slot == None:
                            pass
                    except EOFError:
                        del attr_slots[index]


    def restart(self, config_file=None, mongo_addr=None):
        """Restart the server AND reload the config file and all devices"""
        logger.info('restarting...')
        self.reload_config(config_file)
        self.reload_server_config()
        self.disconnect_mongo()
        self.connect_mongo(mongo_addr)
        self.reload_devices()
        self.reload_server()


    def reload_server_config(self):
        """Reload RPyC server settings from the config"""
        self.port, _ = get_config_param(self.config, \
                        ['port'])


    def connect_mongo(self, mongo_addr=None):
        """Config and connect to the mongodb database"""
        self.db_name = MONGO_SERVERS_KEY.format(self.port)
        if mongo_addr:
            self.mongo_addr = mongo_addr
        else:
            self.mongo_addr,_ = get_config_param(self.config, \
                                                [CONFIG_MONGO_ADDR_KEY])
        logger.info('connecting to mongodb server [{}]...'.\
                        format(self.mongo_addr))
        self.mongo_client = pymongo.MongoClient(mongo_addr,
                            replicaset=MONGO_RS,
                            serverSelectionTimeoutMS=MONGO_CONNECT_TIMEOUT)
        self.db = self.mongo_client[self.db_name]
        self.mongo_client.drop_database(self.db_name)
        logger.info('connected to mongodb server [{}]'.format(self.mongo_addr))


    def disconnect_mongo(self):
        """Disconnect from the mongodb database"""
        if self.mongo_client:
            # remove the database entry from mongo
            self.mongo_client.drop_database(self.db_name)
            # disconnect
            self.mongo_client.close()


    def add_device(self, dev_name):
        """Add and initialize a device"""

        # load the device parameters from the config file

        # first try getting the driver's lantz class
        try:
            dev_lantz_class, dev_class_cfg_file = get_config_param(self.config,
                                        [CONFIG_SERVER_DEVICES, dev_name, \
                                        CONFIG_SERVER_DEVICE_LANTZ_CLASS])
            try:
                dev_class = load_class_from_str('lantz.drivers.' + \
                                                dev_lantz_class)
            except Exception as exc:
                raise InstrumentServerError(exc, 'The specified lantz driver '
                    '[{}] for device [{}] couldn\'t be loaded'.\
                    format(dev_lantz_class, dev_name))
        except ConfigEntryNotFoundError:
            # if the lantz class isn't defined, try getting an absolute file
            # path and class name
            try:
                dev_class_file_str, dev_class_file_cfg_file = \
                                    get_config_param(self.config,
                                            [CONFIG_SERVER_DEVICES, dev_name,
                                            CONFIG_SERVER_DEVICE_CLASS_FILE])
                dev_class_name, _ = get_config_param(self.config,
                                            [CONFIG_SERVER_DEVICES, dev_name,
                                            CONFIG_SERVER_DEVICE_CLASS_NAME])
            except ConfigEntryNotFoundError as exc:
                raise InstrumentServerError(exc, 'The device [{}] didn\'t '
                    'contain an entry for either a lantz class "{}" or a file '
                    'path "{}" / class name "{}" to define it\'s driver type'.\
                    format(dev_name, CONFIG_SERVER_DEVICE_LANTZ_CLASS,
                            CONFIG_SERVER_DEVICE_CLASS_FILE,
                            CONFIG_SERVER_DEVICE_CLASS_NAME))
            dev_class_path = Path(dev_class_file_str)
            
            # resolve relative paths
            if not dev_class_path.is_absolute():
                dev_class_path = Path(dev_class_file_cfg_file).parent / dev_class_path
            dev_class_path = dev_class_path.resolve()

            try:
                dev_class = load_class_from_file(dev_class_path, dev_class_name)
            except Exception as exc:
                raise InstrumentServerError(exc, 'The specified class [{}] '
                    'from file [{}] for device [{}] couldn\'t be loaded'.\
                    format(dev_class_name, dev_class_path, dev_name))

        dev_args, _ = get_config_param(self.config,
                                    [CONFIG_SERVER_DEVICES, dev_name, 'args'])
        dev_kwargs, _ = get_config_param(self.config,
                                    [CONFIG_SERVER_DEVICES, dev_name, 'kwargs'])

        # get an instance of the device
        try:
            self._devs[dev_name] = dev_class(*dev_args, **dev_kwargs)
        except Exception as exc:
            raise InstrumentServerError(exc, 'Failed to get instance of device '
                                        '{} of class {}'.\
                                        format(dev_name, dev_class)) from None

        # collect all of the lantz feature attributes
        feat_attr_list = []
        for feat_name, feat in list(dev_class._lantz_feats.items()) + list(dev_class._lantz_dictfeats.items()):
            if isinstance(feat_name, DictPropertyNameKey):
                # filter out weird dictfeat feats
                continue

            attrs = copy.deepcopy(feat.__dict__['_config'])
            if isinstance(feat, DictFeat) and 'keys' in feat.__dict__:
                attrs['keys'] = feat.__dict__['keys']

            if attrs['limits']:
                if len(attrs['limits']) == 1:
                    limits = [0, attrs['limits'][0]]
                else:
                    limits = attrs['limits']
            else:
                limits = None

            if attrs['values']:
                values = list(attrs['values'])
            else:
                values = None

            if 'keys' in attrs and attrs['keys']:
                keys = list(attrs['keys'])
            else:
                keys = None

            if 'keys' in attrs and attrs['keys'] and isinstance(feat, DictFeat):
                value = [None] * len(attrs['keys'])
            else:
                value = None

            feat_attr_list.append({
                'name':     feat_name,
                'type':     'dictfeat' if isinstance(feat, DictFeat) \
                                            else 'feat',
                'readonly': feat.__dict__['fset'] is None,
                'units':    attrs['units'],
                'limits':   limits,
                'values':   values,
                'keys':     keys,
                'value':    value
            })

            # add a custom hook for updating mongodb whenever the feat/dictfeat is written
            if isinstance(feat, DictFeat):
                def update_mongo_dictfeat(value, old_value, key, attr=feat_name, keys=keys):
                    logger.debug('{}[{}]: {} -> {}'.format(attr, key, old_value, value))
                    if isinstance(value, Quantity):
                        value = value.to(self._devs[dev_name]._lantz_dictfeats[attr]._kwargs['units']).m
                    self.db[dev_name].update_one({'name': attr},
                                                 {'$set': {'value.{}'.format(keys.index(key)): value}},
                                                 upsert=True)

                self.dictfeat_hook_functions[feat_name] = update_mongo_dictfeat
                getattr(self._devs[dev_name], feat_name + '_changed').connect(self.dictfeat_hook_functions[feat_name])
            else:
                def update_mongo_feat(value, old_value, attr=feat_name):
                    logger.debug('{}: {} -> {}'.format(attr, old_value, value))
                    if isinstance(value, Quantity):
                        value = value.to(self._devs[dev_name]._lantz_feats[attr]._kwargs['units']).m
                    self.db[dev_name].update_one({'name': attr},
                                                 {'$set': {'value': value}},
                                                 upsert=True)

                self.feat_hook_functions[feat_name] = update_mongo_feat
                getattr(self._devs[dev_name], feat_name + '_changed').connect(self.feat_hook_functions[feat_name])

        for action_name, action in dev_class._lantz_actions.items():
            feat_attr_list.append({'name' : action_name, 'type' : 'action'})

        self.db[dev_name].drop()
        # add all of the lantz feature attributes to the database
        self.db[dev_name].insert_many(feat_attr_list)

        # initialize the device
        try:
            self._devs[dev_name].initialize()
        except Exception as exc:
            logger.error(exc)
            self._devs.pop(dev_name)
            logger.error('device [{}] initialization sequence failed'.\
                            format(dev_name))
            return

        logger.info('added device [{}] with args: {} kwargs: {}'.\
                        format(dev_name, dev_args, dev_kwargs))


    def del_device(self, dev_name):
        """Remove and finalize a device"""
        try:
            self._devs.pop(dev_name).finalize()
        except Exception as exc:
            raise InstrumentServerError(exc, 'Failed deleting device [{}]'.\
                                        format(dev_name)) from None
        logger.info('deleted [{}]'.format(dev_name))


    def reload_device(self, dev_name):
        """Remove a device, then reload it from the stored config"""
        if dev_name in self._devs:
            self.del_device(dev_name)
        self.add_device(dev_name)


    def reload_devices(self):
        """Reload all devices"""
        devs, _ = get_config_param(self.config, ['devices'])
        for dev_name in devs:
            self.reload_device(dev_name)
        logger.info('reloaded all devices')


    def reload_config(self, config_file=None):
        """Reload the config files"""
        # update the config with a new file if one was passed as argument
        if config_file:
            self.config_file = config_file
        # reload the config dictionary
        self.config = load_config(self.config_file)
        logger.info('loaded config files {}'.\
                        format(list(self.config.keys())))


    def reload_server(self):
        """Restart the RPyC server"""
        self.stop_server()
        self.start_server()


    def start_server(self):
        """Start the RPyC server"""
        if self._rpyc_server:
            logger.warning('can\'t start the rpyc server because one '
                            'is already running')
            return
        thread = threading.Thread(target=self._rpyc_server_thread)
        thread.start()
        # wait for the server to start
        while not (self._rpyc_server and self._rpyc_server.active):
            time.sleep(0.1)


    def stop_server(self):
        """Stop the RPyC server"""
        if not self._rpyc_server:
            logger.warning('can\'t stop the rpyc server because there '
                            'isn\'t one running')
            return
        logger.info('stopping RPyC server...')
        self._rpyc_server.close()
        # wait for the server to stop
        while self._rpyc_server.active:
            time.sleep(0.1)
        RPYC_SERVER_STOP_EVENT.wait()
        RPYC_SERVER_STOP_EVENT.clear()
        self._rpyc_server = None


    def _rpyc_server_thread(self):
        """Thread for running the RPyC server asynchronously"""
        logger.info('starting RPyC server...')
        self._rpyc_server = ThreadedServer(self, port=self.port,
                        protocol_config={'allow_pickle' : True,
                                    'allow_all_attrs' : True,
                                    'allow_setattr' : True,
                                    'allow_delattr' : True,
                                    'sync_request_timeout' : RPYC_SYNC_TIMEOUT})
        self._rpyc_server.start()
        logger.info('RPyC server stopped')
        RPYC_SERVER_STOP_EVENT.set()
