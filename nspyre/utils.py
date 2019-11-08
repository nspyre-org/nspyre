import pymongo

def connect_to_master(mongodb_addrs):
        for addr in mongodb_addrs:
            client = pymongo.MongoClient(addr)
            if client.is_primary:
                print("Connected to Mongo master at: {}".format(addr))
                return client
        raise Exception('Could not find Mongo Master!')

def cleanup_register(client):
    if type(client) is str:
        client = pymongo.MongoClient(client)
    db_list = client['Spyre_Live_Data'].list_collection_names()
    reg_list = [x['_id'] for x in client['Spyre_Live_Data']['Register'].find({},{'_id':True})]
    for name in reg_list:
        if not name in db_list:
            client['Spyre_Live_Data']['Register'].delete_one({'_id': name})