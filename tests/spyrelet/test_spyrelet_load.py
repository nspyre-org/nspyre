"""
This file tests the functionality of the spyrelets

Author: Jacob Feder
Date: 11/13/2020
"""

###########################
# imports
###########################

# std
from pathlib import Path

# nspyre
from nspyre.spyrelet.spyrelet import load_all_spyrelets, unload_all_spyrelets, \
                                    unload_spyrelet, load_spyrelet, reload_all_spyrelets, \
                                    reload_spyrelet, SpyreletLoadError
from nspyre.inserv.gateway import InservGateway

###########################
# tests
###########################

class TestSpyrelets:
    def test_spyrelet_load(self, gateway):
        spyrelets = load_all_spyrelets(gateway)
        unload_all_spyrelets()
        # spyrelets = load_all_spyrelets(gateway)
        # unload_spyrelet('sweep')
        # try:
        #     spyrelets = load_all_spyrelets(gateway)
        #     raise Exception('this should have failed in the previous line')
        # except SpyreletLoadError:
        #     pass
        # load_spyrelet('sweep', gateway)
        # reload_all_spyrelets(gateway)
        # reload_spyrelet('sweep', gateway)
