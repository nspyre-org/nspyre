###########################
# imports
###########################

# std
import logging

# nspyre
from nspyre.spyrelet.spyrelet import Spyrelet
from nspyre.definitions import Q_

# from nspyre.gui.widgets.views import Plot1D, Plot2D, PlotFormatInit, PlotFormatUpdate
# from nspyre.gui.widgets.plotting import LinePlotWidget

###########################
# classes
###########################

class SinglePoint(Spyrelet):
    REQUIRED_DEVICES = [
        'fake_sg',
        'fake_daq',
        'fake_pellicle',
    ]

    PARAMS = {
        'amp': {
            'type': float,
            'units':'V'},
        'freq': {
            'type': float,
            'units':'GHz'},
    }

    def main(self, freq, amp):
        # open the pellicle
        self.fake_pellicle.opened = True
        # set the frequency / amplitude of the sg
        self.fake_sg.amplitude = amp
        self.fake_sg.frequency = freq
        # make an analog input read
        val = self.fake_daq.ain[0]
        # gather the data
        self.acquire({
            'freq': freq,
            'A': amp,
            'result': val,
        })

        # close the pellicle
        self.fake_pellicle.opened = False

    def initialize(self, freq, amp):
        logging.info('initializing [{}]...'.format(self.name))

    def finalize(self, freq, amp):
        logging.info('finalizing [{}]...'.format(self.name))

class FreqAmpSweep(Spyrelet):
    REQUIRED_DEVICES = [
        'fake_sg',
        'fake_daq',
        'fake_pellicle',
        'lantz_scope'
    ]

    PARAMS = {
        'amp_range': {
            'type': range,
            'units':'V'},
        'freq_range': {
            'type': range,
            'units':'GHz'},
    }

    def main(self, freq_range, amp_range):
        # flip up the pellicle
        self.fake_pellicle.opened = True

        # iterate over ampitudes
        for a, amp in enumerate(self.progress(amp_range)):
            self.fake_sg.amplitude = amp
            # iterate over frequencies
            for f, freq in enumerate(self.progress(freq_range)):
                self.fake_sg.frequency = f
                # measure an analog input voltage
                val = self.fake_daq.ain[0]
                # gather the data
                self.acquire({
                    'ind': i,
                    'f': f,
                    'a': a,
                    'A': amplitude,
                    'result': val,
                })

        rand_array = self.lantz_scope.measure()
        self.fake_pellicle.opened = False

    def initialize(self, freq_range, amp_range):
        logging.info('initializing [{}]...'.format(self.name))

    def finalize(self, freq_range, amp_range):
        logging.info('finalizing [{}]...'.format(self.name))

    # @Plot1D
    # def plot_results(df, cache):
    #     return {'result':[df.ind.values, df.result.values]}

    # @Plot1D
    # def plot_f(df, cache):
    #     return {'f':[df.ind.values, df.f.values], 'f2':[df.ind.values, 2*df.f.values]}

    # @PlotFormatInit(LinePlotWidget, ['plot_f', 'plot_results'])
    # def init_formatter(plot):
    #     plot.xlabel = 'My x axis (a.u.)'
    #     plot.ylabel = 'Signal (in bananas)'
