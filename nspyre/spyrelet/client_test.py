import rpyc

con = rpyc.connect('localhost', 5556)
sg = con.root.devs['fake_sg']

import pdb; pdb.set_trace()