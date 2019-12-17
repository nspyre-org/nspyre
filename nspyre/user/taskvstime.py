import numpy as np
import time
from nspyre import *
from itertools import count

from lantz.drivers.ni.simple_daq import Read_DAQ

class TaskVsTime(Spyrelet):
    REQUIRED_DEVICES = {
        'daq': Read_DAQ,
    }

    PARAMS = {
        'channel':          {'type':str},
        'time_per_point':   {'type':float, 'units': 's',},
        'iterations':       {'type':int, 'positive':True},
    }

    def read(self, time_per_point):
        if self.ttype == 'CI':
            cnt = self.daq.read(self.tname, 1)
            time.sleep(time_per_point)
            val = self.daq.read(self.tname, 1)[0] - cnt[0]
            return val/time_per_point 
        if self.ttype == 'AI':
            clock_rate = 8000 #This is a hardcoded value since getting the actual clock rate is difficult right now...
            samples = int(time_per_point*clock_rate)
            return np.mean(self.daq.read(self.tname,samples)[0])

    def main(self, channel, time_per_point, iterations=100):
        start_t = time.time()
        iterator = count() if iterations == 'inf' else range(iterations)
        for i in self.progress(iterator):
            val = self.read(time_per_point.to('s').m)

            self.acquire({
                't': time.time()-start_t,
                'val': val,
            })
            
    def initialize(self, channel, time_per_point, iterations=100):
        self.tname = self.name + '_task'
        self.daq.new_task(self.tname, [channel])
        self.ttype = self.daq.get_task_type(self.tname)
        self.daq.start(self.tname)
        
    def finalize(self, channel, time_per_point, iterations=100):
        self.daq.stop(self.tname)
        self.daq.clear_task(self.tname)
        
    @Plot1D
    def all(df, cache):
        return {'signal':[df.t.values, df.val.values]}

    @Plot1D
    def latest(df, cache):
        return {'signal':[df.t.tail(100).values, df.val.tail(100).values]}