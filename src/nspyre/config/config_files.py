#!/usr/bin/env python
"""
This module handles reading and writing YAML configuration files

Author: Jacob Feder
Date: 7/25/2020
"""

###########################
# imports
###########################

# std
from pathlib import Path
from importlib import import_module
import logging

# 3rd party
import yaml

# nspyre
from nspyre.definitions import join_nspyre_path, CLIENT_META_CONFIG_PATH

###########################
# globals
###########################

logger = logging.getLogger(__name__)

META_CONFIG_FILES_ENTRY = 'config_files'
META_CONFIG_ENABLED_IDX = 'enabled'

###########################
# exceptions
###########################

class ConfigEntryNotFoundError(Exception):
    """Exception for when a configuration file doesn't contain the desired
    entry"""
    def __init__(self, config_path, msg=None):
        if msg is None:
            msg = 'Config file was expected to contain parameter: [{}] ' \
                    'but it wasn\'t found'.format(' -> '.join(config_path))
        super().__init__(msg)
        self.config_path = config_path

class ConfigError(Exception):
    """General Config file exception"""
    def __init__(self, error, msg):
        super().__init__(msg)
        if error:
            logger.exception(error)

###########################
# classes / functions
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
    config_list = meta_config[META_CONFIG_FILES_ENTRY]
    new_files = []
    for f in files:
        f_path = Path(f).resolve()
        if not f_path.is_file():
            raise FileNotFoundError('file [{}] not found'.format(f_path))
        if str(f_path) in config_list:
            raise ConfigError(None, 'the config file {} is already available'.format(f))
        new_files.append(str(f_path))
    meta_config[META_CONFIG_FILES_ENTRY] = config_list + new_files
    write_config(meta_config, meta_config_file)

def meta_config_remove(meta_config_file, files):
    """Remove config files from the meta-config"""
    meta_config = load_raw_config(meta_config_file)
    enabled_idx = meta_config[META_CONFIG_ENABLED_IDX]
    config_list = meta_config[META_CONFIG_FILES_ENTRY]
    # list of indicies to remove from config_list
    pop_list = []
    # go through the list of config files / indicies and generate
    # a list of indicies to remove
    for c in files:
        try:
            idx = int(c)
        except ValueError:
            # the user passed the config name as a string, so we should first
            # find its index
            try:
                idx = meta_config[META_CONFIG_FILES_ENTRY].index(c)
            except ValueError as exc:
                raise ConfigError(exc, 'config file [{}] was not found in the '
                                'meta-config - check that the file path shown '
                                'using --list-configs matches given input'.\
                                format(c)) from None
        pop_list.append(idx)

    pop_list.sort(reverse=True)
    new_enabled_idx = enabled_idx
    for idx in pop_list:
        try:
            config_list.pop(idx)
            # if an item before the enabled one was deleted we have to decrement
            # the enabled index
            if idx < enabled_idx:
                new_enabled_idx -= 1
        except IndexError as exc:
            raise ConfigError(exc, 'tried to remove config file index [{}] '
                'that was out of range'.format(idx))

    # if the user removed the currently enabled config
    if enabled_idx in pop_list:
        new_enabled_idx = 0

    meta_config[META_CONFIG_FILES_ENTRY] = config_list
    meta_config[META_CONFIG_ENABLED_IDX] = new_enabled_idx
    write_config(meta_config, meta_config_file)

def meta_config_files(meta_config_file):
    """Return the paths of the config files in the meta-config"""
    meta_config = load_raw_config(meta_config_file)
    config_list = meta_config[META_CONFIG_FILES_ENTRY]
    return config_list

def meta_config_enabled_idx(meta_config_file):
    """Return the index of the enabled config"""
    meta_config = load_raw_config(meta_config_file)
    return meta_config[META_CONFIG_ENABLED_IDX]

def meta_config_set_enabled_idx(meta_config_file, idx_or_str):
    """Return the index of the enabled config"""
    meta_config = load_raw_config(meta_config_file)
    try:
        idx = int(idx_or_str)
    except ValueError:
        # the user passed the config name as a string, so we should first
        # find its index
        try:
            idx = meta_config[META_CONFIG_FILES_ENTRY].index(idx_or_str)
        except ValueError as exc:
            raise ConfigError(exc, 'config file [{}] was not found in the '
                'meta-config - check that the file path shown '
                'using --list-configs matches given input'.\
                format(idx_or_str)) from None
    meta_config[META_CONFIG_ENABLED_IDX] = idx
    write_config(meta_config, meta_config_file)

def load_meta_config(meta_config_path=None):
    """Takes a 'meta' config file and returns the file path of the activated 
    config file"""

    # TODO this logic should be removed and meta_config_path always passed in
    if not meta_config_path:
        meta_config_path = CLIENT_META_CONFIG_PATH

    # load the meta config
    meta_config = load_raw_config(meta_config_path)
    # get the index of the enabled config file
    enabled_idx = meta_config[META_CONFIG_ENABLED_IDX]

    # get the config file path
    config_files = meta_config[META_CONFIG_FILES_ENTRY]
    if not config_files:
        raise ConfigError(None, 'no configuration files exist - '
                    'use nspyre-config --add-config to add files') from None
    cfg_path = Path(config_files[enabled_idx])

    # resolve relative paths
    if not cfg_path.is_absolute():
        cfg_path = meta_config_path.parent / cfg_path
    cfg_path = cfg_path.resolve()
    
    return cfg_path

def load_config(cfg_path):
    """Load a config file and return the configuration as a dictionary"""
    try:
        cfg_dict = {str(cfg_path): load_raw_config(cfg_path)}
    except FileNotFoundError as exc:
        raise ConfigError(exc, 'configuration file [{}] doesn\'t exist'.\
                            format(cfg_path)) from None
    return cfg_dict

def write_config(config_dict, filepath):
    """Write a dictionary to a YAML file"""
    # open the file and write it's config dictionary
    with open(filepath, 'w') as file:
        yaml.dump(config_dict, file, default_flow_style=False)

def get_config_param(config_dict, path):
    """Navigate a YAML-loaded config file and return a particular parameter 
    given by 'path'. If multiple config files contain the first element of
    'path', this will attempt to navigate the the first config file it finds
    that contains the first element of 'path'."""
    first_elem = path[0]
    for conf in config_dict:
        # first find the config file containing the first path element
        loc = config_dict[conf]
        if first_elem in loc:
            # now descend into the config dictionary, following the keys
            # one-by-one in path
            for p in path:
                try:
                    loc = loc[p]
                except KeyError:
                    raise ConfigEntryNotFoundError(path) from None
            return loc, conf
    # if we reach this point the first path element wasn't found in any
    # config file entries
    raise ConfigEntryNotFoundError(path) from None
