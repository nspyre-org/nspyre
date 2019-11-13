"""
    spyre.widgets.instrument_manager.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This instrument manager is a Widget which can connect to an Instrument server and control the associated devices

    Author: Alexandre Bourassa
    Date: 10/30/2019
"""

import pymongo

from nspyre.instrument_server import Instrument_Server_Client, load_remote_device
from nspyre.mongo_listener import Synched_Mongo_Database
from nspyre.utils import get_configs

class Instrument_Manager():

    def __init__(self, instrument_server_client_list=None):
        if instrument_server_client_list is None:
            instrument_server_client_list = []
            for server in get_configs()['instrument_servers_addrs']:
                instrument_server_client_list.append(Instrument_Server_Client(**server))
        # Compile a list of zmq and mongo client objects
        self.clients = list()
        self.fully_mongo = True
        for c in instrument_server_client_list:
            db = c.get_mongodb()
            if db is None:
                self.fully_mongo = False
                self.clients.append({'zmq':c,'mongo':None})
            else:
                mc = pymongo.MongoClient(db['server_addrs'])
                self.clients.append({'zmq':c, 'mongo':mc[db['db_name']]})

        # Create the instrument list
        self.instr = dict()
        for c in self.clients:
            for dname in c['zmq'].list_instr():
                self.update_instr(dname, c)

        

    def launch_watchers(self):
        for c in self.clients:
            addr = "mongodb://{}:{}/".format(*c['mongo'].client.address)
            db_name = c['mongo'].name
            c['watcher'] = Synched_Mongo_Database(db_name, addr)


    def update_instr(self, dname, client):
        instr_dict = client['zmq'].list_instr()
        if not dname in instr_dict:
            if dname in self.instr:
                self.instr.pop(dname)
            return None
        else:
            self.instr[dname] = {
                'zmq': client['zmq'],
                'mongo': client['mongo'][dname],
                'class': instr_dict[dname]['class'],
                'dev': load_remote_device(client['zmq'], dname)
            }
            return self.instr[dname]

    def del_instr(self, dname, client):
        client['zmq'].del_instr(dname)
        self.update_instr(dname, client)
        
    def add_instr(self, dname, client, dclass, *args, **kwargs):
        client['zmq'].add_instr(dname, dclass, *args, **kwargs)
        self.update_instr(dname, client)
        return 

    def get_devices(self):
        return {dname : self.instr[dname]['dev'] for dname in self.instr}

    def get(self, dname):
        if dname in self.instr:
            return self.instr[dname]
        else:
            for c in self.clients:
                if dname in c['zmq'].list_instr():
                    return self.update_instr(dname, c)
            raise Exception('Could not find device: {}'.format(dname))