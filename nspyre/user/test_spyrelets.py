from lantz.drivers.examples.dummydrivers import DummyOsci
from lantz.drivers.examples.fungen import LantzSignalGenerator
import numpy as np
import time
from nspyre.views import Plot1D, Plot2D, PlotFormatInit, PlotFormatUpdate
from nspyre.spyrelet import Spyrelet
from nspyre.widgets.plotting import LinePlotWidget
from nspyre.colors import colors
from itertools import cycle

COLORS = cycle(colors.keys())

class SubSpyrelet(Spyrelet):
    REQUIRED_DEVICES = {
        'sg': LantzSignalGenerator,
    }

    PARAMS = {
        'iterations':{
            'type':int,
            'positive':True},
    }

    def main(self, iterations, A=1.1):
        for i in self.progress(range(iterations)):
            self.sg.amplitude = A
            time.sleep(0.1)
            # print(i)
            # time.time()
            self.acquire({
                'ind': i,
                'rand': np.random.uniform(1,2, 100),
                'freq': self.sg.frequency,
            })
    @Plot1D
    def last_rand(df, cache):
        last_rand = np.array(df.rand.iloc[-1])
        return {'rand':[np.arange(len(last_rand)), last_rand]}

    @Plot1D
    def avg_rand(df, cache):
        rand = np.array(list(df.rand.values))
        return {'rand':[df.ind.values, rand.mean(axis=1)]}

    @Plot2D
    def data_im(df, cache):
        im = np.array(list(df.rand.values))
        return im


    @PlotFormatUpdate(LinePlotWidget, ['last_rand'])
    def formatter(plot, df, cache):
        for item in plot.plot_item.listDataItems():
            item.setPen(colors[next(COLORS)])

class MyExperiment(Spyrelet):
    REQUIRED_DEVICES = {
        'sg': LantzSignalGenerator,
        'osc': DummyOsci
    }

    REQUIRED_SPYRELETS = {
        's2': SubSpyrelet
    }

    PARAMS = {
        'amplitude':{
                'type': float,
                'units':'V'},
        'fs':{
            'type': range,
            'units':'GHz'},
    }

    def main(self, fs, amplitude):
        for i, f in enumerate(self.progress(fs)):
            self.sg.frequency = f
            # print(f)
            self.call(self.s2, 100, A=amplitude)
            # print(self.s2.data)
            val = self.s2.data.rand.mean().mean()
            # print(val)
            self.acquire({
                'ind':i,
                'f':f,
                'A':amplitude,
                'result': val,
            })

    def initialize(self, fs, amplitude):
        print('initialize')

    def finalize(self, fs, amplitude):
        print('finalize')

    @Plot1D
    def plot_results(df, cache):
        return {'result':[df.ind.values, df.result.values]}

    @Plot1D
    def plot_f(df, cache):
        return {'f':[df.ind.values, df.f.values], 'f2':[df.ind.values, 2*df.f.values]}

    @PlotFormatInit(LinePlotWidget, ['plot_f', 'plot_results'])
    def init_formatter(plot):
        plot.xlabel = 'My x axis (a.u.)'
        plot.ylabel = 'Signal (in bananas)'


    
    

# if __name__=='__main__':
#     from nspyre.instrument_manager import Instrument_Manager
#     from nspyre.instrument_server import Instrument_Server_Client
#     mongodb_addrs = ["mongodb://localhost:27017/","mongodb://localhost:27018/"]
#     c = Instrument_Server_Client(ip='localhost', port='5556')
#     m = Instrument_Manager([c])
#     sg  = m.get('sg')
#     s2 = SubSpyrelet('s2', mongodb_addrs, m)
#     s1 = MyExperiment('myExp', mongodb_addrs, m, {'s2':s2})