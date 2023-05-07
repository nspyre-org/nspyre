"""
This file tests the functionality of the instrument server and gateway.

Author: Jacob Feder
Date: 11/12/2020
"""
import logging

import pytest
from nspyre import InstrumentGateway
from nspyre import InstrumentGatewayError

logger = logging.getLogger(__name__)


class TestInserv:
    def test_connect(self, gateway):
        """Test the gateway can connect and have an empty dict of devices"""
        assert not gateway._devs

    def test_connect_fail(self):
        """Test the gateway returns an error if the ip is wrong"""
        with pytest.raises(InstrumentGatewayError):
            with InstrumentGateway(addr='an invalid ip!'):
                pass

    def test_device_add_from_file(self, gateway_with_devs):
        """Test the gateway fixture contains drivers that were loaded from files"""
        assert 'daq' in gateway_with_devs._devs
        assert 'pel' in gateway_with_devs._devs
        assert 'sg' in gateway_with_devs._devs
        assert 'not_a_driver' not in gateway_with_devs._devs

    def test_device_mgmt(self, gateway_with_devs):
        """Test the gateway can restart and remove devices"""
        gateway_with_devs.restart('daq')
        assert gateway_with_devs.daq
        gateway_with_devs.remove('daq')
        with pytest.raises(AttributeError):
            gateway_with_devs.daq
