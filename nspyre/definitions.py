import os

# root directory of nspyre
NSPYRE_ROOT = os.path.dirname(os.path.abspath(__file__))

def _join_nspyre_path(path):
    """Return a full path from a path given relative to the nspyre root 
    directory"""
    return os.path.join(NSPYRE_ROOT, path)

# config files
CLIENT_META_CONFIG_YAML =  _join_nspyre_path('config/client_meta_config.yaml')
SERVER_META_CONFIG_YAML = _join_nspyre_path('config/server_meta_config.yaml')

# mongodb replicaset name
MONGO_RS = 'NSpyreSet'
# Mongodb instrument server databases will contain a special document
# that contains the instrument server settings
MONGO_SERVERS_SETTINGS = '_settings'
# All instrument server databases in mongodb will be of this form
MONGO_SERVERS_KEY = 'inserv[{}]'
# All experiment databases in mongodb will be of this form
MONGO_EXPERIMENTS_KEY = 'experiment[{}]'
# in ms
MONGO_CONNECT_TIMEOUT = 5000