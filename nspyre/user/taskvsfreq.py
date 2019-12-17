import numpy as np
import time
from nspyre import *
from itertools import count

from lantz.drivers.ni.simple_daq import Read_DAQ
from lantz.drivers.stanford.sg396 import SG396

class TaskVsFreq(Spyrelet):
    REQUIRED_DEVICES = {
        'sg':  SG396,
        'daq': Read_DAQ,
    }

    PARAMS = {
        'fs':               {'type': range, 'units':'GHz'},
        'ch1':              {'type':str},
        'ch2':              {'type':str},
        'rf_power':         {'type':float},
        'time_per_point':   {'type':float, 'units': 's'},
        'iterations':       {'type':int, 'positive':True},
    }

    def read(self, time_per_point):
        if self.ttype == 'CI':
            ctrs_start = np.array([[self.daq.read(tname,1)[0], time.time()] for tname in self.tnames])
            time.sleep(time_per_point)
            ctrs_end = np.array([[self.daq.read(tname,1)[0], time.time()] for tname in self.tnames])
            diff_ctrs = ctrs_end - ctrs_start
            ctrs_rates = diff_ctrs[:,0] / diff_ctrs[:,1]
            return ctrs_rates
        if self.ttype == 'AI':
            clock_rate = 8000 #This is a hardcoded value since getting the actual clock rate is difficult right now...
            samples = int(time_per_point*clock_rate)
            return np.mean(self.daq.read(self.tname,samples), axis=1)

    def main(self, fs, ch1, ch2, rf_power, time_per_point=0.5, iterations=100):
        time_per_point = time_per_point.to('s').m
        start_t = time.time()
        iterator = count() if iterations == 'inf' else range(iterations)
        for i in self.progress(iterator):
            for f in self.progress(fs):
                self.sg.frequency = f
                vals = self.read(time_per_point)
                self.acquire({
                    'i': i,
                    't': time.time()-start_t,
                    'f': f.to('GHz').m,
                    'ch1': vals[0],
                    'ch2': vals[1],
                })
            
    def initialize(self, fs, ch1, ch2, rf_power, time_per_point=0.5, iterations=100):
        self.sg.rf_amplitude = rf_power
        self.sg.rf_toggle = True
        self.sg.mod_toggle = True
        num_ctr = sum([1 for ch in [ch1, ch2] if 'ctr' in ch])
        if num_ctr == 2:
            self.ttype = 'CI'
            self.daq.new_task(self.name+'_task_ch1', [ch1])
            self.daq.new_task(self.name+'_task_ch2', [ch2])
            self.tnames = [self.name+'_task_ch1', self.name+'_task_ch2']
            [self.daq.start(name) for name in self.tnames]
        elif num_ctr == 0:
            self.ttype = 'AI'
            self.daq.new_task(self.name+'_task', [ch1, ch2])
            self.tnames = [self.name+'_task']
            self.daq.start(self.name+'_task')
        else:
            raise Exception("Can't handle {} counter channels.  Both channels must be counters or both channels must be analog")
        
    def finalize(self, fs, ch1, ch2, rf_power, time_per_point=0.5, iterations=100):
        self.sg.rf_toggle = False
        for name in self.tnames:
            self.daq.stop(name)
            self.daq.clear_task(name)
        
    @Plot1D
    def avg(df, cache):
        g = df.groupby('f')
        fs = g.ch1.mean().index
        return {'ch1':[fs, g.ch1.mean()],'ch2':[fs, g.ch2.mean()]}

    @Plot1D
    def latest(df, cache):
        latest = df[df.i == df.i.max()]
        return {'ch1':[latest.index, latest.ch1],'ch2':[latest.index, latest.ch2]}

    @Plot1D
    def diff_avg(df, cache):
        g = df.groupby('f')
        fs = g.ch1.mean().index
        return {'ch1-ch2':[fs, g.ch1.mean()-g.ch2.mean()]}

    @Plot1D
    def diff_latest(df, cache):
        latest = df[df.i == df.i.max()]
        return {'ch1-ch2':[latest.index, latest.ch1-latest.ch2]}

    @PlotFormatInit(LinePlotWidget, ['avg', 'latest', 'diff_avg', 'diff_latest'])
    def init_plot(plot):
        plot.xlabel = 'Frequency (GHz)'
        plot.ylabel = 'Signal'