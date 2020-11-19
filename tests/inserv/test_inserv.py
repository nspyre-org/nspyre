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

# std
import logging

# nspyre
from nspyre.inserv.gateway import InservGateway
from nspyre.definitions import Q_

###########################
# globals
###########################

logger = logging.getLogger(__name__)

###########################
# tests
###########################

class TestInserv:
    def test_feats_get_set(self, gateway):
        """test basic feat get/set"""
        gateway.tserv.fake_sg.amplitude = Q_(1.0, 'V')
        assert gateway.tserv.fake_sg.amplitude == Q_(1.0, 'V')
        gateway.tserv.fake_sg.amplitude = Q_(10.0, 'V')
        assert gateway.tserv.fake_sg.amplitude == Q_(10.0, 'V')

    def test_feats_units(self, gateway):
        """test get/set with different pint units"""
        gateway.tserv.fake_sg.amplitude = Q_(0.1, 'V')
        assert gateway.tserv.fake_sg.amplitude == Q_(100.0, 'mV')
        gateway.tserv.fake_sg.amplitude = Q_(10, 'mV')
        assert gateway.tserv.fake_sg.amplitude == Q_(0.01, 'V')

    def test_dictfeats_get_set(self, gateway):
        """test basic dictfeat get/set"""
        for k in range(1, 10):
            gateway.tserv.fake_daq.dout[k] = False
            assert gateway.tserv.fake_daq.dout[k] == False
        for k in range(1, 10):
            gateway.tserv.fake_daq.dout[k] = True
            assert gateway.tserv.fake_daq.dout[k] == True

    def test_dictfeats_ro(self, gateway):
        """test read-only dictfeats"""
        gateway.tserv.fake_daq.reset_din(False)
        for k in range(1, 10):
            assert gateway.tserv.fake_daq.din[k] == False
            gateway.tserv.fake_daq.toggle_din(k)
            assert gateway.tserv.fake_daq.din[k] == True
