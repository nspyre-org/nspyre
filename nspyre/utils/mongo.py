import pymongo

def get_mongo_client(mongodb_addr=None):
	if mongodb_addr is None:
		cfg = get_configs()
		mongodb_addr = cfg['mongodb_addr']
	return pymongo.MongoClient(mongodb_addr, replicaset='NSpyreSet')