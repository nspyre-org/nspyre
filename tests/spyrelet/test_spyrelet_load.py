"""
This file tests the functionality of the spyrelets

Author: Jacob Feder
Date: 11/13/2020
"""

###########################
# imports
###########################

# nspyre
from nspyre.spyrelet.spyrelet import load_all_spyrelets, unload_all_spyrelets, \
                                    unload_spyrelet, load_spyrelet, reload_all_spyrelets, \
                                    reload_spyrelet, SpyreletLoadError
from nspyre.inserv.gateway import InservGateway

###########################
# tests
###########################

class TestSpyrelets:
    def test_spyrelet_load(client_config_path):
        pass
        # with InservGateway(client_config_path) as im:
        #     import pdb; pdb.set_trace()
        #     spyrelets = load_all_spyrelets(im)
        #     unload_all_spyrelets()
        #     spyrelets = load_all_spyrelets(im)
        #     unload_spyrelet('sweep')
        #     try:
        #         spyrelets = load_all_spyrelets(im)
        #         raise Exception('this should have failed in the previous line')
        #     except SpyreletLoadError:
        #         pass
        #     load_spyrelet('sweep', im)
        #     reload_all_spyrelets(im)
        #     reload_spyrelet('sweep', im)
