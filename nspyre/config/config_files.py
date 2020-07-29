import yaml
import os
from importlib import import_module

META_CONFIG_FILES_ENTRY = 'config_files'

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

class ConfigError(Exception):
    """General Config file exception"""
    def __init__(self, msg):
        super().__init__(msg)

###########################
# Classes / functions
###########################

# A meta-config.yaml file contains a single entry with key 
# META_CONFIG_FILES_ENTRY and value = a list of all the config files that
# should be read

def load_raw_config(filepath):
    """Return a config file dictionary loaded from a YAML file"""
    with open(filepath, 'r') as f:
        conf = yaml.safe_load(f)
    return conf

def meta_config_add(meta_config_file, files):
    """Add config files to the meta-config"""
    meta_config = load_raw_config(meta_config_file)
    config_list = get_config_param(meta_config, [META_CONFIG_FILES_ENTRY])
    new_files = []
    for f in files:
        if os.path.isabs(f):
            f_name = f
        else:
            f_name = os.path.abspath(os.path.join(os.getcwd(), f))
        if not os.path.isfile(f_name):
            raise FileNotFoundError('file %s not found' % (f_name))
        new_files.append(f_name)
    meta_config[META_CONFIG_FILES_ENTRY] = config_list + new_files
    write_config(meta_config, meta_config_file)

def meta_config_remove(meta_config_file, files):
    """Remove config files from the meta-config"""
    meta_config = load_raw_config(meta_config_file)
    config_list = get_config_param(meta_config, [META_CONFIG_FILES_ENTRY])
    for c in files:
        try:
            c_int = int(c)
            # ran if c is an integer indicating an index rather than a file path
            config_list.pop(c_int)
        except:
            # otherwise c is a file path string
            if c in config_list:
                config_list.remove(c)
            else:
                raise ConfigError('config file %s was not found in the '
                                    'meta-config' % (c)) from None
    meta_config[META_CONFIG_FILES_ENTRY] = config_list
    write_config(meta_config, meta_config_file)

def meta_config_files(meta_config_file):
    meta_config = load_raw_config(meta_config_file)
    config_list = get_config_param(meta_config, [META_CONFIG_FILES_ENTRY])
    return config_list

def load_config(filepath):
    """Takes a 'meta' config file that specifies the location of other config
    files to load, then make a dictionary that is a union of the dictionaries in
    the specified configs. Repeated dictionary entries in different config files
    will be overwritten."""
    # load the meta config
    meta_config = load_raw_config(filepath)
    # get the config file paths
    config_files = get_config_param(meta_config, ['config_files'])
    union_dict = {}
    # iterate through the config file paths, load their dictionaries, and add
    # them to the combined dictionary, overwriting keys/values if redefined
    # TODO do a recursive dictionary union rather than replace/overwrite?
    meta_config_dir = os.path.dirname(filepath)
    for cfg_file in config_files:
        if not os.path.isabs(cfg_file):
            cfg_file = os.path.join(meta_config_dir, cfg_file)
        union_dict.update(load_raw_config(cfg_file))
    # return the final config dictionary as well as the files that were loaded
    return (union_dict, config_files)

def write_config(config_dict, filepath):
    """Write a dictionary to a YAML file"""
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
