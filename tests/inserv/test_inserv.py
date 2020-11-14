"""
This file tests the functionality of the instrument server and gateway. It 
presumes that mongodb and the instrument server have been started from 
conftest.py by pytest.

Author: Jacob Feder
Date: 11/12/2020
"""

###########################
# imports
###########################

# nspyre
from nspyre.inserv.gateway import InservGateway
from nspyre.definitions import Q_

###########################
# tests
###########################

def test_feats(client_config_path):
    with InservGateway(client_config_path) as insgw:
        insgw.tserv.fake_sg.amplitude = Q_(1.0, 'V')
        assert insgw.tserv.fake_sg.amplitude == Q_(1.0, 'V')
        insgw.tserv.fake_sg.amplitude = Q_(10.0, 'V')
        assert insgw.tserv.fake_sg.amplitude == Q_(10.0, 'V')

def test_dictfeats(client_config_path):
    with InservGateway(client_config_path) as insgw:
        for k in range(1, 10):
            insgw.tserv.fake_daq.dout[k] = True
            assert insgw.tserv.fake_daq.dout[k] == True
        for k in range(1, 10):
            insgw.tserv.fake_daq.dout[k] = False
            assert insgw.tserv.fake_daq.dout[k] == False
        for k in range(1, 10):
            insgw.tserv.fake_daq.dout[k] = True
            assert insgw.tserv.fake_daq.dout[k] == True
