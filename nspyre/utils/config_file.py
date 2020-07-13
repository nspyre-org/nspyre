import yaml
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
	"""Return a config file dictionary loaded from a YAML file"""
	with open(filepath, 'r') as f:
		conf = yaml.safe_load(f)
	return conf

def get_config_param(config_dict, path):
	"""Navigate a YAML-loaded config file and return a particular parameter"""
	loc = config_dict
	for p in path:
		try:
			loc = loc[p]
		except KeyError:
			raise ConfigEntryNotFoundError(path) from None
	return loc

def get_class_from_str(class_str):
	class_name = class_str.split('.')[-1]
	mod = import_module(class_str.replace('.' + class_name, ''))
	return getattr(mod, class_name)
