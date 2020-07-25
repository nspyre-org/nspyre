"""
    nspyre.spyrelet.instrument_manager.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module manages and centralizes connections to one or more instrument
    servers

    Author: Jacob Feder
    Date: 7/11/2020
"""

from nspyre.utils.config_file import get_config_param, load_config
from nspyre.utils.misc import MonkeyWrapper
from pint import Quantity
import os
import logging
import rpyc

###########################
# Globals
###########################

this_dir = os.path.dirname(os.path.realpath(__file__))

###########################
# Exceptions
###########################

class InstrumentManagerError(Exception):
    """General InstrumentManager exception"""
    def __init__(self, msg):
        super().__init__(msg)

###########################
# Classes / functions
###########################

class Instrument_Manager():
    """Loads a configuration file, then attempts to connect to all specified
        instrument servers"""
    def __init__(self, config_file):
        self.config = {}
        self.servers = {}
        self.update_config(config_file)
        self.connect_servers()

    def connect_servers(self):
        """Attempt connection to all of the instrument servers specified in
        the config file"""
        servers_configs = get_config_param(self.config, ['instrument_servers'])
        for s in servers_configs:
            s_addr = get_config_param(self.config,
                                    ['instrument_servers', s, 'address'])
            s_port = get_config_param(self.config,
                                    ['instrument_servers', s, 'port'])
            self.connect_server(s, s_addr, s_port)

    def disconnect_servers(self):
        """Attempt disconnection from all of the instrument servers"""
        for s in list(self.servers):
            self.disconnect_server(s)

    def connect_server(self, s_id, s_addr, s_port):
        """Attempt connection to an instrument server"""
        try:
            self.servers[s_id] = rpyc.connect(s_addr, s_port)
            # this allows the instrument server to have full access to this
            # client's object dictionaries - necessary for some lantz commands
            self.servers[s_id]._config['allow_all_attrs'] = True
        except:
            raise InstrumentManagerError('Failed to connect to '
                            'instrument server [%s] at address [%s]'
                            % (s_id, s_addr)) from None
        logging.info('instrument manager connected to server [%s]' % (s_id))

    def disconnect_server(self, s_id):
        """Disconnect from an instrument server and remove it's associated 
        devices"""
        try:
            self.servers[s_id].close()
            del self.servers[s_id]
        except:
            raise InstrumentManagerError('Failed to disconnect from '
                            'instrument server [%s]' % (s_id)) from None
        logging.info('instrument manager disconnected '
                        'from server [%s]' % (s_id))

    def get_devices(self):
        """Iterate through the devices in the config file and attempt to 
        load the associated devices from the instrument servers"""
        devs = {}
        config_devs = get_config_param(self.config, ['devices'])
        for d in config_devs:
            # get the server associated with the device
            s_id = get_config_param(self.config, ['devices', d, 'server_id'])
            if not s_id in self.servers:
                raise InstrumentManagerError('Device [%s] instrument server '
                                    '[%s] not found in "instrument_servers"'
                                    % (d, s_id)) from None
                        
            # get the server device name associated with the device
            s_dev = get_config_param(self.config, ['devices', d,
                                                    'server_device'])

            # pint has an associated unit registry, and Quantity objects
            # cannot be shared between registries. Because Quantity objects
            # coming from the instrument server have a different unit registry,
            # they must be converted to Quantity objects of the local registry.
            # see pint documentation for details
            def dev_get_attr(obj, attr):
                ret = getattr(obj, attr)
                if isinstance(ret, Quantity):
                    try:
                        quantity_ret = Quantity(ret.m, str(ret.u))
                    except:
                        raise InstrumentManagerError('Instrument server [%s] '
                            'device (manager) [%s]<->[%s] (server) attribute '
                            '[%s] returned a unit not found in the pint unit '
                            'registry' % (s_id, d, s_dev, attr))
                    return quantity_ret
                else:
                    return ret

            # retrieve the actual device object from the instrument server
            try:
                # see inserv.py and RPyC documentation for how
                # the device is retrieved from the instrument server
                # monkey wrap the device so we can override it's getter
                # to fix pint unit registry issue
                devs[d] = MonkeyWrapper(self.servers[s_id].root.devs[s_dev],
                                        get_attr_override=dev_get_attr)
            except:
                raise InstrumentManagerError('Instrument server [%s] has no '
                            'loaded device [%s]' % (s_id, s_dev)) from None

            logging.info('instrument manager loaded device [%s] from '
                            ' server [%s]' % (d, s_id))
        return devs

    def update_config(self, config_file):
        """Reload the config file"""
        filename = os.path.join(this_dir, config_file)
        self.config = load_config(filename)

    def __enter__(self):
        """Python context manager setup"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Python context manager teardown"""
        self.disconnect_servers()

if __name__ == '__main__':
    # configure server logging behavior
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s -- %(levelname)s -- %(message)s',
                        handlers=[logging.StreamHandler()])
    with Instrument_Manager('config.yaml') as im:
        devs = im.get_devices()
        devs['my_sg1'].amplitude = Quantity(1.0, 'volt')
        print('found devices:\n%s' % (devs))
        print(Quantity(5, 'volt') + devs['my_sg1'].amplitude)