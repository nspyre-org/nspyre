"""
    nspyre.spyrelet.instrument_manager.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module manages and centralizes connections to one or more instrument
    servers

    Author: Jacob Feder
    Date: 7/11/2020
"""

from nspyre.utils.config_file import get_config_param, load_config
from nspyre.utils.utils import monkey_wrap
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

            # retrieve the actual device object from the instrument server
            try:
                # see inserv.py and RPyC documentation for how this works
                devs[d] = self.servers[s_id].root.devs[s_dev]
            except:
                raise InstrumentManagerError('Instrument server [%s] has no '
                            'loaded device [%s]' % (s_id, s_dev)) from None

            # TODO Q_ object registry conversion

            logging.info('instrument manager loaded device [%s] from '
                            ' server [%s]' % (d, s_id))
        return devs

    def update_config(self, config_file):
        """Reload the config file"""
        filename = os.path.join(this_dir, config_file)
        self.config = load_config(filename)

    # TODO finalize -> self.disconnect_servers()

if __name__ == '__main__':
    # configure server logging behavior
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s -- %(levelname)s -- %(message)s',
                        handlers=[logging.StreamHandler()])
    im = Instrument_Manager('config.yaml')
    import pdb; pdb.set_trace()
    print(im.get_devices())
