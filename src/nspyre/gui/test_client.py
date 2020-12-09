from nspyre.inserv.gateway import InservGateway
import pdb

if __name__ ==  '__main__':
    ig = InservGateway()
    sg = ig.local1._devs['fake_tcpip_sg']
    sg.offset = 1
    print(sg.offset)
    #pdb.set_trace()
