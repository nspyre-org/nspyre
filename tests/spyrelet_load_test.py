import nspyre.spyrelet.spyrelet
from nspyre.inserv.gateway import InservGateway

with InservGateway() as im:
    sp = nspyre.spyrelet.spyrelet.load_all_spyrelets(im)
    nspyre.spyrelet.spyrelet.unload_all_spyrelets()
    sp = nspyre.spyrelet.spyrelet.load_all_spyrelets(im)
    nspyre.spyrelet.spyrelet.unload_spyrelet('s2')
    try:
        sp = nspyre.spyrelet.spyrelet.load_all_spyrelets(im)
    except:
        pass
    nspyre.spyrelet.spyrelet.load_spyrelet('s2', im)
    nspyre.spyrelet.spyrelet.reload_all_spyrelets(im)
    nspyre.spyrelet.spyrelet.reload_spyrelet('s2', im)
