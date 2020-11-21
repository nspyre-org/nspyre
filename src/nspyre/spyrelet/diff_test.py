import pickle
import xdelta3
import logging

def test_diff_performance():
    import numpy as np
    import time
    import random

    data_dim = 1000
    watched_var = np.random.rand(data_dim, data_dim)

    n_iterations = 10

    avg_pickle_time = 0
    avg_delta_time = 0
    avg_undelta_time = 0
    avg_unpickle_time = 0

    last_pack = pickle.dumps(watched_var)
    for i in range(n_iterations):

        for i in range(1000):
            watched_var[np.random.randint(1, data_dim)][np.random.randint(1, data_dim)] = 5.0        

        start_time = time.time()
        curr_pack = pickle.dumps(watched_var)
        pickle_time = time.time()
        avg_pickle_time += pickle_time - start_time
        delta = xdelta3.encode(last_pack, curr_pack)
        delta_time = time.time()
        avg_delta_time += delta_time - pickle_time
        unpack = xdelta3.decode(last_pack, delta)
        undelta_time = time.time()
        avg_undelta_time += undelta_time - delta_time
        remote_var = pickle.loads(unpack)
        unpickle_time = time.time()
        avg_unpickle_time += unpickle_time - undelta_time
        assert watched_var.all() == remote_var.all()
        print(  f'pickle {pickle_time - start_time:.5f}s '
                f'delta {delta_time - pickle_time:.5f}s '
                f'undelta {undelta_time - delta_time:.5f}s '
                f'unpickle {unpickle_time - undelta_time:.5f}s')
    avg_pickle_time /= n_iterations
    avg_delta_time /= n_iterations
    avg_undelta_time /= n_iterations
    avg_unpickle_time /= n_iterations
    save_time_start = time.time()
    np.save('test', watched_var)
    save_time = time.time() - save_time_start
    print('--------------------------- avg ---------------------------')
    print(  f'pickle {avg_pickle_time:.5f}s '
            f'delta {avg_delta_time:.5f}s '
            f'undelta {avg_undelta_time:.5f}s '
            f'unpickle {avg_unpickle_time:.5f}s')
    print(f'save {save_time}s')

if __name__ == '__main__':
    test_diff_performance()
