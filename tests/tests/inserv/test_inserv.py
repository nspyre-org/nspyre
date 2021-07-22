"""
This file tests the functionality of the instrument server and gateway.

Author: Jacob Feder
Date: 11/12/2020
"""

import logging
import atexit
import subprocess
import time
import datetime

import pytest

from nspyre import InstrumentGateway, InstrumentGatewayError, Q_
from pint import UnitRegistry

logger = logging.getLogger(__name__)


class TestInserv:
    def test_connect(self, gateway):
        """Test the gateway can connect and have an empty dict of devices"""
        assert not gateway.devs

    def test_connect_fail(self, inserv):
        """Test the gateway returns an error if the ip is wrong"""
        with pytest.raises(InstrumentGatewayError) as e_info:
            not_a_gateway = InstrumentGateway(addr='an invalid ip!')

    def test_device_add_from_file(self, gateway_with_devs):
        """Test the gateway fixture contains drivers that were loaded from files"""
        assert 'daq' in gateway_with_devs.devs
        assert 'pel' in gateway_with_devs.devs
        assert 'sg' in gateway_with_devs.devs
        assert 'not_a_driver' not in gateway_with_devs.devs

    def test_device_mgmt(self, gateway_with_devs):
        """Test the gateway can restart and remove devices"""
        gateway_with_devs.restart('daq')
        assert gateway_with_devs.daq
        gateway_with_devs.remove('daq')
        with pytest.raises(AttributeError) as e_info:
            gateway_with_devs.daq

    def test_device_add_from_module(self, gateway, free_port):
        """Test the gateway should be able to load a driver by importing from an
        installed python module e.g. lantz"""

        # start the lantz example voltmeter process
        vm_proc = subprocess.Popen(
            ['lantz-sims', 'voltmeter', 'tcp', '--port', str(free_port)], stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        # make sure the inserv gets killed on exit even if there's an error
        def cleanup():
            vm_proc.kill()

        atexit.register(cleanup)
        # wait for the process to start
        time.sleep(0.5)

        # add the driver to the inserv
        gateway.add(
            'vm', 'lantz.drivers.examples', 'LantzVoltmeter', f'TCPIP::localhost::{free_port}::SOCKET', import_or_file='import'
        )

        # lantz requires drivers to be initialized before use
        gateway.vm.initialize()
        # try to get the voltage to see if the devices is really connected
        gateway.vm.voltage[0]

        # stop the lantz voltmeter process
        vm_proc.kill()

    def test_feats_get_set(self, gateway_with_devs):
        """Test basic lantz feat get/set"""
        gateway_with_devs.sg.amplitude = Q_(1.0, 'V')
        assert gateway_with_devs.sg.amplitude == Q_(1.0, 'V')
        gateway_with_devs.sg.amplitude = Q_(10.0, 'V')
        assert gateway_with_devs.sg.amplitude == Q_(10.0, 'V')

    def test_feats_units(self, gateway_with_devs):
        """test get/set with different pint units"""
        gateway_with_devs.sg.amplitude = Q_(0.1, 'V')
        assert gateway_with_devs.sg.amplitude == Q_(100.0, 'mV')
        gateway_with_devs.sg.amplitude = Q_(10, 'mV')
        assert gateway_with_devs.sg.amplitude == Q_(0.01, 'V')

    def test_dictfeats_get_set(self, gateway_with_devs):
        """test basic dictfeat get/set"""
        for k in range(1, 10):
            gateway_with_devs.daq.dout[k] = False
            assert gateway_with_devs.daq.dout[k] == False
        for k in range(1, 10):
            gateway_with_devs.daq.dout[k] = True
            assert gateway_with_devs.daq.dout[k] == True

    def test_dictfeats_ro(self, gateway_with_devs):
        """test read-only dictfeats"""
        gateway_with_devs.daq.reset_din(False)
        for k in range(1, 10):
            assert gateway_with_devs.daq.din[k] == False
            gateway_with_devs.daq.toggle_din(k)
            assert gateway_with_devs.daq.din[k] == True
