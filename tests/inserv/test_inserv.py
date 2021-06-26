"""
This file tests the functionality of the instrument server and gateway.

Author: Jacob Feder
Date: 11/12/2020
"""

import logging

logger = logging.getLogger(__name__)

class TestInserv:
    def test_connect(self, gateway):
        """Test the gateway connection connected properly and contains our drivers"""
        assert 'daq' in gateway.devs
        assert 'pel' in gateway.devs
        assert 'sg' in gateway.devs
        assert 'not_a_driver' not in gateway.devs

    # def test_device_mgmt(self, gateway):
    #     gateway.add('test', 'path', 'class')
    #     gateway.restart('test')
    #     gateway.remove('test')


    # def test_feats_get_set(self, gateway):
    #     """test basic feat get/set"""
    #     gateway.fake_sg.amplitude = Q_(1.0, 'V')
    #     assert gateway.fake_sg.amplitude == Q_(1.0, 'V')
    #     gateway.fake_sg.amplitude = Q_(10.0, 'V')
    #     assert gateway.fake_sg.amplitude == Q_(10.0, 'V')

    # def test_feats_units(self, gateway):
    #     """test get/set with different pint units"""
    #     gateway.fake_sg.amplitude = Q_(0.1, 'V')
    #     assert gateway.fake_sg.amplitude == Q_(100.0, 'mV')
    #     gateway.fake_sg.amplitude = Q_(10, 'mV')
    #     assert gateway.fake_sg.amplitude == Q_(0.01, 'V')

    # def test_dictfeats_get_set(self, gateway):
    #     """test basic dictfeat get/set"""
    #     for k in range(1, 10):
    #         gateway.fake_daq.dout[k] = False
    #         assert gateway.fake_daq.dout[k] == False
    #     for k in range(1, 10):
    #         gateway.fake_daq.dout[k] = True
    #         assert gateway.fake_daq.dout[k] == True

    # def test_dictfeats_ro(self, gateway):
    #     """test read-only dictfeats"""
    #     gateway.fake_daq.reset_din(False)
    #     for k in range(1, 10):
    #         assert gateway.fake_daq.din[k] == False
    #         gateway.fake_daq.toggle_din(k)
    #         assert gateway.fake_daq.din[k] == True
