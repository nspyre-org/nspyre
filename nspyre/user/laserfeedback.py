import numpy as np
import time
from nspyre import *
from itertools import count

from lantz.drivers.toptica import DLC
from lantz.drivers.toptica.highfinesse_ws7 import WS7

class LaserFeedback(Spyrelet):
    REQUIRED_DEVICES = {
        'dlc':  DLC,
        'ws7': WS7,
    }

    PARAMS = {
        'freq':             {'type': float, 'units':'GHz'},
        'fb_period':        {'type': float, 'units':'s'},
        'num_of_period':    {'type':int, 'nonnegative':True},
        'continuous':       {'type': bool},
        # 'tolerance':        {'type': float, 'units':'GHz'},
        # 'p':                {'type': float, 'units':'V / GHz'},
    }

    CONSTS = {
        'ws7_ch': 1,
        'p': Q_(1.5, 'V/GHz')
    }

    def main(self, freq, fb_period=0.5, num_of_period=10, continuous=False):
        piezo_voltage = self.dlc.piezo_voltage
        start_time = time.time()
        iterator = count() if continuous else range(num_of_period)
        for iteration in self.progress(iterator):
            if iteration%100 == 99:
                # time.sleep(0.1)# To avoid clear during plotting 
                self.clear_data() # Prevent unecessary accumulation of data

            #Calc the piezo correction
            curr_freq = self.ws7.frequency[self.CONSTS['ws7_ch']]
            df = curr_freq - freq
            dpiezo = self.CONSTS['p'] * df

            #Apply the piezo correction
            piezo_voltage -= dpiezo
            if not Q_(0, 'V') <= piezo_voltage <= Q_(140, 'V'):
                # piezo value out of range
                raise Exception('Target Piezo Value exceeded allowed range (V={})'.format(piezo_voltage))
            self.dlc.piezo_voltage = piezo_voltage

            self.acquire({
                'iteration': iteration,
                'time': time.time() - start_time,
                'freq_error': df.to('MHz').m,
                'piezo_voltage': piezo_voltage.to('V').m
                })
            time.sleep(fb_period.to('s').m)
            
    def initialize(self, freq, fb_period=0.5, num_of_period=10, continuous=False):
        pass
        
    def finalize(self, freq, fb_period=0.5, num_of_period=10, continuous=False):
        pass
        
    @Plot1D
    def frequency_error(df, cache):
        return {'ch1':[df.time, df.freq_error]}

    @PlotFormatInit(LinePlotWidget, ['frequency_error'])
    def init_plot(plot):
        plot.xlabel = 'Time (s)'
        plot.ylabel = 'Error (MHz)'