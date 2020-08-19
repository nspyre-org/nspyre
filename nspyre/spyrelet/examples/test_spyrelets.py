###########################
# imports
###########################

# std
import numpy as np
import time
from itertools import cycle
import logging

# nspyre
from nspyre.gui.widgets.views import Plot1D, Plot2D, PlotFormatInit, PlotFormatUpdate
from nspyre.spyrelet.spyrelet import Spyrelet
from nspyre.gui.widgets.plotting import LinePlotWidget
from nspyre.gui.colors import colors
from nspyre.definitions import Q_

COLORS = cycle(colors.keys())

###########################
# classes
###########################

class SubSpyrelet(Spyrelet):
    REQUIRED_DEVICES = [
        'sg'
    ]

    PARAMS = {
        'iterations':{
            'type':int,
            'positive':True},
        'amplitude':{
            'type':float,
            'positive':True},
    }

    def main(self, iterations, amplitude):
        for i in self.progress(range(iterations)):
            self.sg.amplitude = amplitude
            time.sleep(0.1)
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
    REQUIRED_DEVICES = [
        'sg',
        'osc'
    ]

    REQUIRED_SPYRELETS = {
        's2': SubSpyrelet
    }

    PARAMS = {
        'amplitude': {
                'type': float,
                'units':'V'},
        'fs': {
            'type': range,
            'units':'GHz'},
    }

    def main(self, fs, amplitude):
        for i, f in enumerate(self.progress(fs)):
            self.sg.frequency = f
            self.call(self.s2, 100, amplitude)
            val = self.s2.data.rand.mean().mean()
            self.acquire({
                'ind':i,
                'f':f,
                'A':amplitude,
                'result': val,
            })

    def initialize(self, fs, amplitude):
        logging.info('initializing [{}]...'.format(self.name))

    def finalize(self, fs, amplitude):
        logging.info('finalizing [{}]...'.format(self.name))

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