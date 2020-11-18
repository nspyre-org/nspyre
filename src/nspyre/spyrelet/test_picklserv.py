"""
Testing for future spyrelet data acquisition system
1. variables that will contain experimental data are tagged with self.watch(var)
2. on each call to self.progress(), the watched vars are pickled and pushed to a queue
3. the pickle server runs in a separate thread, and pops pickles off the queue
4. each pickle is diff'ed with the previous pickle
5. the diff is sent over the network to any remote processes interested in consuming the data
6. the original objects are reconstructed in real-time from the diffs

Author: Jacob Feder
Date: 11/17/2020
"""

import pickle
import difflib
import random
import copy
import logging
import numpy as np

def hex_str(byte_arr):
    return ''.join(format(x, ' 02x') for x in byte_arr)

def test_pickleserv():

    random.seed()

    watched_var = {50:[1, 2, 3], 'a':'test', 60:np.array([3.4, 6.0])}
    for i in range(100):
        watched_var[i] = random.randint(0, 100)
    curr_pickle = pickle.dumps(watched_var)
    remote_pickle = copy.copy(curr_pickle)

    for i in range(10000):
        # pick a number of changes to make
        nchanges = random.randint(1, 10)
        for c in range(nchanges):
            # pick an operation to perform on that index (delete or replace/add)
            op = random.randint(0, 1)
            if op:
                # pick a random key
                idx = random.randint(0, 100)
                # replace or add with a new random value
                watched_var[idx] = random.randint(0, 100)
            else:
                if len(watched_var):
                    # pick a random (existing) key
                    idx_key = list(watched_var.keys())[random.randint(0, len(watched_var) - 1)]
                    # delete that key
                    del watched_var[idx_key]

        # pickle the watched variables
        last_pickle = copy.copy(curr_pickle)
        curr_pickle = pickle.dumps(watched_var)

        # find the diffs with the previous pickle
        diffs = []
        # when bytes are deleted or inserted, the byte indices between the last 
        # and current pickle become offset - this variable keeps track of that offset 
        # so that the diffs array contains indices relevant to the object at that moment
        offset = 0
        # use difflib's algorithm to generate a set of simple operations that turn
        # last_pickle into curr_pickle - see difflib docs on get_opcodes()
        matcher = difflib.SequenceMatcher(None, last_pickle, curr_pickle)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            i1 += offset
            i2 += offset
            if tag == 'replace' or tag == 'insert':
                # replace indicies i1:i2 in last_pickle with j1:j2 of curr_pickle
                diffs.append( (i1, i2, curr_pickle[j1:j2]) )
                offset = offset + ((j2 - j1) - (i2 - i1))
            elif tag == 'delete':
                # delete i1:i2 of last_pickle
                diffs.append( (i1, i2, b'') )
                offset = offset - (i2 - i1)
            elif tag == 'equal':
                pass
            else:
                raise Exception

        # the diffs array is then sent to the remote system

        # the remote uses the diffs to reconstruct the new object
        for d in diffs:
            i1 = d[0]
            i2 = d[1]
            inser_str = d[2]
            remote_pickle = remote_pickle[:i1] + inser_str + remote_pickle[i2:]

        remote_var = pickle.loads(remote_pickle)

        assert watched_var == remote_var
        
        logging.info('last:{}'.format(hex_str(last_pickle)))
        logging.info('last:{}'.format(hex_str(curr_pickle)))
        logging.info('remo:{}'.format(hex_str(remote_pickle)))
        logging.info(watched_var)
        logging.info(remote_var)

if __name__ == '__main__':
    from nspyre.misc.logging import nspyre_init_logger
    nspyre_init_logger(logging.INFO)
    test_pickleserv()
