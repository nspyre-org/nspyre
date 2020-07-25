import yaml
import os
from importlib import import_module

###########################
# Exceptions
###########################

class ConfigEntryNotFoundError(Exception):
    """Exception for when a configuration file doesn't contain the desired
    entry"""
    def __init__(self, config_path, msg=None):
        if msg is None:
            msg = 'Config file was expected to contain parameter: { %s } ' \
                    'but it wasn\'t found.' % \
                    (' -> '.join(config_path))
        super().__init__(msg)
        self.config_path = config_path

###########################
# Classes / functions
###########################

def load_config(filepath):
    """Takes a 'meta' config file that specifies the location of other config
    files to load, then make a dictionary that is a union of the dictionaries in
    the specified configs"""
    # load the meta config
    meta_config = load_raw_config(filepath)
    # get the config file paths
    config_files = get_config_param(meta_config, ['config_files'])
    union_dict = {}
    # iterate through the config file paths, load their dictionaries, and add
    # them to the combined dictionary, overwriting keys/values if redefined
    # TODO should probably do a recursive dictionary union rather than replace
    for cfg_file in config_files:
        union_dict.update(load_raw_config(cfg_file))
    return union_dict

def load_raw_config(filepath):
    """Return a config file dictionary loaded from a YAML file"""
    # deal with absolute vs relative paths
    if not os.path.isabs(filepath):
        filepath = os.path.join(os.getcwd(), filepath)
    # open the file and load it's config dictionary
    with open(filepath, 'r') as f:
        conf = yaml.safe_load(f)
    return conf

def write_config(config_dict, filepath):
    """Write a dictionary to a YAML file"""
    # deal with absolute vs relative paths
    if not os.path.isabs(filepath):
        filepath = os.path.join(os.getcwd(), filepath)
    # open the file and write it's config dictionary
    with open(filepath, 'w') as file:
        yaml.dump(config_dict, file)

def get_config_param(config_dict, path):
    """Navigate a YAML-loaded config file and return a particular parameter"""
    loc = config_dict
    for p in path:
        try:
            loc = loc[p]
        except KeyError:
            raise ConfigEntryNotFoundError(path) from None
    return loc
