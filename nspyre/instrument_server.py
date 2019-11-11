"""
    spyre.instrument_server.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This creates an instrument server (and an associated client) that creates a communication channel between a ZMQ network connection and
    a set of lantz instruments.

    WARNING: This is still experimental.  It uses serialize the object which is not secure over unencrypted connection in an untrusted environment.

    Author: Alexandre Bourassa
    Date: 10/30/2019

"""
VERSION = '0.1'

from lantz import Q_, Feat, DictFeat, Action
from lantz.feat import MISSING

import msgpack
import msgpack_numpy as m
m.patch()
import numpy as np
import time
from importlib import import_module
import zmq
import traceback
import socket

try:    
    import pymongo
except:
    print("WARNING: Pymongo is not installed.  You won't be able to use the MongoDB_Instrument_Server")


# Serialization Custom type: Quantity
def custom_encode(obj):
    if isinstance(obj, Q_):
        # This format could potentially be optimized (by reducing the length of strings), 
        # but this most likelly won't be limitting
        return {b'__Quantity__': True, b'm': obj.m, b'units': str(obj.units)}
    return obj

def custom_decode(obj):
    if b'__Quantity__' in obj:
        obj = Q_(obj[b'm'], obj[b'units'])
    return obj

class InstrumentServerError(Exception):
    pass

class ServerUnreachableError(Exception):
    pass


class Instrument_Server():
    """
        This is the base instrument server without MongoDB signalling 
    """
    DEBUG = True

    def __init__(self,  server_name, port):
        self.name = server_name
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:{}".format(port))

        self.COMMANDS = {
            'ID':self.get_id,
            'COMMAND_LIST': self.get_commands,
            'PING':self.ping,
            'ADD_INSTR':self.add_instr,
            'DEL_INSTR':self.del_instr,
            'LIST_INSTR':self.list_instr,
            'GET_INSTR_INFO':self.get_instr_info,
            'INITIALIZE': self.initialize_instr,
            'FINALIZE': self.finalize_instr,
            'GET_FEAT':self.get_feat,
            'SET_FEAT':self.set_feat,
            'GET_DICTFEAT':self.get_dictfeat,
            'SET_DICTFEAT':self.set_dictfeat,
            'RUN_ACTION': self.run_action,
            'GET_MONGODB':self.get_mongodb,
        }

        self.instr = {}
        self.instr_info = {}

    def get_mongodb(self):
        return None
    
    def send(self, obj):
        ser = msgpack.packb(obj, use_bin_type=True, default=custom_encode)
        return self.socket.send(ser)

    def recv(self):
        ser = self.socket.recv()
        return msgpack.unpackb(ser, raw=False, object_hook=custom_decode)

    def serve_forever(self):
        while True:
            try:
                req = self.recv()
                reply = self.answer_request(req)
                self.send({'status':'ok', 'data':reply})
            except Exception as e:
                if self.DEBUG:
                    traceback.print_exc()
                error_str = traceback.format_exc()
                self.send({'status':'error', 'data':error_str})
    
    def answer_request(self, req):
        """
        Request format is a dict of the form
            {'cmd':<COMMAND str>, 'args':[], 'kwargs':{}}
        """
        # Check proper format
        if not isinstance(req, dict):
            raise Exception("Request must be a dict of the form {'cmd':<COMMAND str>, 'args':[], 'kwargs':{}}")
        elif not 'cmd' in req:
            raise Exception("Request must have a 'cmd' parametter")
        elif not req['cmd'] in self.COMMANDS:
            raise Exception("Invalid command")
        #Execute the command
        else:
            args = req.get('args', [])
            kwargs = req.get('kwargs', {})
            return self.COMMANDS[req['cmd']](*args, **kwargs)

    def get_id(self):
        hostname = socket.gethostname()    
        IPAddr = socket.gethostbyname(hostname) 
        return "{}\n\tInstrument server v{}\n\tIP: {} ({})\n\tPort: {}".format(self.name, VERSION, IPAddr, hostname, self.port)

    def get_commands(self):
        return list(self.COMMANDS.keys())

    def ping(self, send_time):
        return [send_time, time.time()]

    def add_instr(self, dname, dclass, *args, **kwargs):
        class_name = dclass.split('.')[-1]
        mod = import_module(dclass.replace('.'+class_name, ''))
        c = getattr(mod, class_name)
        self.instr[dname] = c(*args, **kwargs)
        self.instr_info[dname] = {'class':dclass, 'args':args, 'kwargs':kwargs}
        self.initialize_instr(dname)
        return "Instrument added!"

    def del_instr(self, dname):
        try:
            self.instr_info.pop(dname)
            d = self.instr.pop(dname)
            d.finalize()
        finally:
            return "Instrument deleted!"

    def list_instr(self):
        return {dname:self.instr_info[dname] for dname in self.instr}

    def get_instr_info(self, dname):
        return self.instr_info[dname]

    def initialize_instr(self, dname):
        return self.instr[dname].initialize()

    def finalize_instr(self, dname):
        return self.instr[dname].finalize()

    # @TODO Maybe worth adding some checks here to verify these are valid feat, dictfeat or action
    def get_feat(self, dname, feat):
        return getattr(self.instr[dname], feat)

    def set_feat(self, dname, feat, val):
        return setattr(self.instr[dname], feat, val)

    def get_dictfeat(self, dname, feat, key):
        return getattr(self.instr[dname], feat)[key]

    def set_dictfeat(self, dname, feat, key, val):
        getattr(self.instr[dname], feat)[key] = val

    def run_action(self, dname, action, *args, **kwargs):
        return getattr(self.instr[dname], action)(*args, **kwargs)






class Instrument_Server_Client():
    def __init__(self, ip, port, recv_timeout=1000):
        self.server_ip = ip
        self.server_port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://{}:{}".format(ip,port))
        self.socket.RCVTIMEO = recv_timeout
        self.socket.linger = recv_timeout
    
    
    def send(self, obj):
        ser = msgpack.packb(obj, use_bin_type=True, default=custom_encode)
        return self.socket.send(ser)

    def recv(self):
        ser = self.socket.recv()
        return msgpack.unpackb(ser, raw=False, object_hook=custom_decode)

    def send_cmd(self, cmd, *args, **kwargs):
        try:
            self.send({'cmd':cmd, 'args':args, 'kwargs':kwargs})
            reply = self.recv()
            if 'status' in reply and 'data' in reply:
                if reply['status'] == 'ok':
                    return reply['data']
                else:
                    raise InstrumentServerError(reply['data'])
            else:
                raise InstrumentServerError('Invalid reply!')
        except (zmq.error.Again,zmq.error.ZMQError):
            print("Could not reach the server")
            self.socket.close()
            raise ServerUnreachableError("Could not reach the server")

    def get_id(self):
        return self.send_cmd('ID')

    def get_commands(self):
        return self.send_cmd('COMMAND_LIST')

    def ping(self):
        ans = self.send_cmd('PING', time.time())
        ans.append(time.time())
        print("Loopback time: {}ms".format((ans[2]-ans[0])*1000))
        print("Estimated clock diff: {} +/- {}ms".format(((ans[2]+ans[0])/2-ans[1])*1000, 1000*(ans[2]-ans[0])/2) )
        return ans

    def add_instr(self, dname, dclass, *args, **kwargs):
        return self.send_cmd('ADD_INSTR', dname, dclass, *args, **kwargs)

    def del_instr(self, dname):
        return self.send_cmd('DEL_INSTR', dname)

    def list_instr(self):
        return self.send_cmd('LIST_INSTR')

    def get_instr_info(self, dname):
        return self.send_cmd('GET_INSTR_INFO', dname)

    def get_feat(self, dname, feat):
        return self.send_cmd('GET_FEAT', dname, feat)

    def set_feat(self, dname, feat, val):
        return self.send_cmd('SET_FEAT', dname, feat, val)

    def initialize_instr(self, dname):
        return self.send_cmd('INITIALIZE', dname)

    def finalize_instr(self, dname):
        return self.send_cmd('FINALIZE', dname)

    def get_dictfeat(self, dname, feat, key):
        return self.send_cmd('GET_DICTFEAT', dname, feat, key)

    def set_dictfeat(self, dname, feat, key, val):
        return self.send_cmd('SET_DICTFEAT', dname, feat, key, val)

    def run_action(self, dname, action, *args, **kwargs):
        return self.send_cmd('RUN_ACTION', dname, action, *args, **kwargs)

    def get_mongodb(self):
        return self.send_cmd('GET_MONGODB')

    def get_none_feat(self, dname):
        return self.send_cmd('GET_NONE_FEAT', dname)



class Remote_Device():
    pass


def load_remote_device(instr_server_client, dname):

    info = instr_server_client.get_instr_info(dname)

    class_name = info['class'].split('.')[-1]
    mod = import_module(info['class'].replace('.'+class_name, ''))
    driver_class = getattr(mod, class_name)

    class Remote_Device_Instance(Remote_Device):
        def __init__(self):
            self.client, self.dname, self.info = instr_server_client, dname, info 

    for feat_name, feat in driver_class._lantz_features.items():
        if isinstance(feat, DictFeat):
            def get_remote_dictfeat(_feat_name):
                class Remote_DictFeat():
                    # This is not ideal, but it will do for now
                    # Ideally I would have a _self reference here instead of the more static instr_server_client and dname
                    def __getitem__(self, key):
                        return instr_server_client.get_dictfeat(dname, _feat_name, key)
                    def __setitem__(self, key, val):
                        return instr_server_client.set_dictfeat(dname, _feat_name, key, val)
                return Remote_DictFeat
            setattr(Remote_Device_Instance, feat_name, get_remote_dictfeat(feat_name)())
        elif isinstance(feat, Feat):
            def get_fun(_feat_name):
                def f_(_self):
                    return _self.client.get_feat(_self.dname, _feat_name)
                return f_

            def set_fun(_feat_name):
                def f_(_self, val):
                    return _self.client.set_feat(_self.dname, _feat_name, val)
                return f_ 

            setattr(Remote_Device_Instance, feat_name, property(get_fun(feat_name), set_fun(feat_name)))

    for action_name, action in driver_class._lantz_actions.items():
        def execute(_action_name):
            def f_(_self, *args, **kwargs):
                return _self.client.run_action(_self.dname, _action_name, *args, **kwargs)
            return f_
        setattr(Remote_Device_Instance, action_name, execute(action_name))

    return Remote_Device_Instance()


class MongoDB_Instrument_Server(Instrument_Server):
    def __init__(self, server_name, port, mongodb_addrs):
        super().__init__(server_name=server_name, port=port)
        self.db_name = 'Instrument_Server[{}]'.format(self.name)
        self.mongodb_addrs = mongodb_addrs
        client = self.connect_to_master()
        client.drop_database(self.db_name)

        self.COMMANDS.update({
            'GET_NONE_FEAT':self.get_none_feat,
        })

    def connect_to_master(self):
        for addr in self.mongodb_addrs:
            client = pymongo.MongoClient(addr)
            if client.is_primary:
                print("Connected to Mongo master at: {}".format(addr))
                self.mongodb_master_addr = addr
                self.db = client[self.db_name]
                return client
        raise Exception('Could not find Mongo Master!')

    def serve_forever(self):
        while True:
            try:
                req = self.recv()
                reply = self.answer_request(req)
                self.send({'status':'ok', 'data':reply})
            except pymongo.errors.NotMasterError:
                print('Got a NotMasterError')
                if self.DEBUG:
                    traceback.print_exc()
                print("Reconnecting to master...")
                self.connect_to_master()
                print('Connected')
                # Try again
                reply = self.answer_request(req)
                self.send({'status':'ok', 'data':reply})
            except Exception as e:
                if self.DEBUG:
                    traceback.print_exc()
                error_str = traceback.format_exc()
                self.send({'status':'error', 'data':error_str})

    def get_mongodb(self):
        return {'db_name':self.db_name, 'server_addr':self.mongodb_master_addr}

    def get_id(self):
        hostname = socket.gethostname()    
        IPAddr = socket.gethostbyname(hostname) 
        return "{}\n\tMongoDB instrument server v{}\n\tIP: {} ({})\n\tPort: {}\n\tDatabase name: {}".format(self.name, VERSION, IPAddr, hostname, self.port, self.db_name)      

    def add_instr(self, dname, dclass, *args, **kwargs):
        ans = super().add_instr(dname, dclass, *args, **kwargs)
        self.db[dname].drop()

        class_name = dclass.split('.')[-1]
        mod = import_module(dclass.replace('.'+class_name, ''))
        c = getattr(mod, class_name)

        doc_list = list()
        for feat_name, feat in c._lantz_features.items():
            params = feat.modifiers[MISSING][MISSING]
            values = list(params['values'].keys()) if not params['values'] is None else None
            if 'keys' in params and not params['keys'] is None:
                keys = list(params['keys'])
                keys.sort()
            else:
                keys = None
            limits = params['limits']
            if not limits is None:
                if len(limits) == 1:
                    limits = [0, limits[0]]
                elif len(limits) == 3:
                    limits = [limits[0], limits[1]]
                    # step = limits[2] #Not used right now

            doc_list.append({
                                'name':feat_name,
                                'type': 'dictfeat' if isinstance(feat, DictFeat) else 'feat',
                                'readonly': dict(self.instr[dname].feats.items())[feat_name].feat.fset is None,
                                'units': params['units'],
                                'limits': limits,
                                'values': values,
                                'keys': keys,
                                'value': [None]*len(params['keys']) if isinstance(feat, DictFeat) else None,
                            })
        for action_name, action in c._lantz_actions.items():
            doc_list.append({
                                'name':action_name,
                                'type': 'action',
                            })

        self.db[dname].insert_many(doc_list)
        return ans

    def get_none_feat(self, dname):
        feats = self.db[dname].find({},{'_id':False, 'name':True, 'value':True, 'type':True, 'keys':True})
        for feat in feats:
            if feat['type'] == 'feat' and feat['value'] is None:
                self.get_feat(dname, feat['name'])
            elif feat['type'] == 'dictfeat':
                for i, key in enumerate(feat['keys']):
                    if feat['value'][i] is None:
                        self.get_dictfeat(dname, feat['name'], key)
        return

    def del_instr(self, dname):
        ans = super().del_instr(dname)
        self.db[dname].drop()
        return ans

    def get_feat(self, dname, feat):
        ans = super().get_feat(dname, feat)
        val = ans.m if isinstance(ans, Q_) else ans
        self.db[dname].update_one({'name':feat},{'$set':{'value':val}}, upsert=True)
        return ans

    def set_feat(self, dname, feat, val):
        ans = super().set_feat(dname, feat, val)
        base_units = self.instr[dname]._lantz_features[feat].modifiers[MISSING][MISSING]['units']
        val = val.to(base_units).m if isinstance(val, Q_) else val
        self.db[dname].update_one({'name':feat},{'$set':{'value':val}}, upsert=True)
        return ans

    def get_dictfeat(self, dname, feat, key):
        ans = super().get_dictfeat(dname, feat, key)
        val = ans.m if isinstance(ans, Q_) else ans
        keys = list(self.instr[dname]._lantz_features[feat].modifiers[MISSING][MISSING]['keys'])
        keys.sort()
        self.db[dname].update_one({'name':feat},{'$set':{'value.{}'.format(keys.index(key)):val}}, upsert=True)
        return ans

    def set_dictfeat(self, dname, feat, key, val):
        ans = super().set_dictfeat(dname, feat, key, val)
        base_units = self.instr[dname]._lantz_features[feat].modifiers[MISSING][MISSING]['units']
        val = val.to(base_units).m if isinstance(val, Q_) else val
        keys = list(self.instr[dname]._lantz_features[feat].modifiers[MISSING][MISSING]['keys'])
        keys.sort()
        self.db[dname].update_one({'name':feat},{'$set':{'value.{}'.format(keys.index(key)):val}}, upsert=True)
        return ans



if __name__ == '__main__':
    from nspyre.utils import get_configs
    cfg = get_configs()
    server = MongoDB_Instrument_Server(**cfg['instrument_server'], mongodb_addrs=cfg['mongodb_addrs'])
    
    # Add the different instruments
    for dname, dev in cfg['device_list'].items():
        try:
            t = time.time()
            server.add_instr(dname, dev[0], *dev[1], **dev[2])
            print('Loaded {} in {:2f}s'.format(dname, time.time()-t))
        except:
            print('Could not load {}'.format(dname))
            traceback.print_exc()
    print("Server ready...")
    server.serve_forever()