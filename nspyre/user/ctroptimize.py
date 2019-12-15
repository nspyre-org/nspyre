import time
import numpy as np
import pyqtgraph as pg

from nspyre import *

from lantz import Q_
from lantz.drivers.toptica import DLC
from lantz.drivers.thorlabs.fabryperot import FabryPerot
from lantz.drivers.sainsmart.relay import Relay

import cma
import dlib

class CTROptimize(Spyrelet):
    REQUIRED_DEVICES = {
        'dlc': DLC,
        'fp': FabryPerot,
        'relay': Relay,
    }

    PARAMS = {
        'piezo_scan_range':    {'type':float, 'units': 'V',},
        'maxevals':            {'type':int, 'nonnegative':True},
        'initial_current':     {'type':float, 'units': 'mA',},
        'initial_feedforward': {'type':float, 'units':'mA/V'},
        'max_retries':         {'type':int}
    }

    # These are parametters which are unlikelly to be changes (but can still be explicitelly changed by the user)
    CONSTS = {
        'ch1_state':         False,
        'ch4_state':         False,
        'current_bounds':    [200,260],
        'feedfoward_bounds': [-1.5,1.5],
        'current_scaling':  Q_(50, 'mA'),
        'settling_time':     Q_(0.1,'s'),
        'optimizer':         'dlib',
        'error_threshold':   30,
        'verbose':           True,
        'error_metric':      'peak height uniformity',
    }

    # Optimization function
    def cost_func(self, x):
        # Set the new values of current and feedfoward
        current, ff = x
        self.dlc.current = current * self.CONSTS['current_scaling']
        self.dlc.feedforward_factor = Q_(ff, 'mA / V')
        time.sleep(self.CONSTS['settling_time'].to('s').m)

        # Compute the error
        # st = time.time()
        self.fp.refresh() #selectivity=0.1
        # print("Fabry Perot 1 took {}s".format(time.time()-st))

        ts = np.linspace(0, self.fp.period.to('ms').m, self.fp.points)
        self.latest_fp_data = [ts, self.fp.trace(), self.fp.peak_locations(), self.fp.peak_magnitudes()]
        
        
        #Calculate error metric
        peak_uniformity_err = np.mean((1 - self.fp.peak_magnitudes())**2)*len(self.fp.peak_magnitudes())**2
        peak_spacing_err = -np.mean(np.diff(self.fp.peak_locations())**2)

        self.reg_cache_store(ts=ts, trace=self.fp.trace(), peaks_loc=self.fp.peak_locations(), peaks_mag=self.fp.peak_magnitudes())
        values = {
            'current': current,
            'feedforward': ff,
            'peak_uniformity_err':peak_uniformity_err,
            'peak_spacing_err':peak_spacing_err,
            'time':time.time()-self.start_time,
        }
        self.acquire(values)

        try:
            next(self.inner_progress)
        except StopIteration:
            pass

        if self.error_metric == 'peak height uniformity':
            return peak_uniformity_err
        elif self.error_metric == 'peak spacing maximize':
            return peak_spacing_err
        else:
            raise Exception("Error metric must be either: \n\t- 'peak height uniformity'\n\t- 'peak spacing maximize'")

    def main(self, piezo_scan_range=Q_(30,'V'), maxevals=50, initial_current=Q_(220,'mA'), initial_feedforward=Q_(-0.2, 'mA/V'), max_retries =2):
        #Set the optimization parametters
        sigma0 = 1
        x0 = [
            (initial_current.to('mA')/self.CONSTS['current_scaling'].to('mA')).m,
            initial_feedforward.to('mA / V').m,
        ]

        bounds = [[self.CONSTS['current_bounds'][0] / self.CONSTS['current_scaling'].to('mA').m, self.CONSTS['feedfoward_bounds'][0]],
                  [self.CONSTS['current_bounds'][1] / self.CONSTS['current_scaling'].to('mA').m, self.CONSTS['feedfoward_bounds'][1]]]

        cmaopts = {
            'tolfun':self.CONSTS['error_threshold'],
            'tolx': 1e-2,
            'maxfevals': maxevals,
            'bounds': bounds,
            'verb_disp':self.CONSTS['verbose'],# No printing of the optimization results on the console
        }

        for retry_idx in self.progress(range(max_retries)):
            #Set to passive mode
            self.fp.active_mode = False
            self.dlc.scan_enabled = True
            self.dlc.piezo_external_input_enabled = True

            #Run the optimization
            self.inner_progress = iter(self.progress(range(maxevals)))
            if self.CONSTS['optimizer'] == 'cma':
                result = cma.fmin(self.cost_func, x0, sigma0, options=cmaopts)
                xopt = result[0]
            elif self.CONSTS['optimizer'] == 'dlib':
                _f = lambda current, ff: self.cost_func([current, ff])
                result = dlib.find_min_global(_f, bounds[0], bounds[1], maxevals)
                xopt = result[0]
            
            #Set the optimal parameters
            err = self.cost_func(xopt)

            #Verify the results
            self.fp.refresh()
            peak_mags = self.fp.peak_magnitudes()
            restart = False

            # If there is too many peak => Restart
            if len(peak_mags) > self.num_peak_threshold:
                restart = True
                if self.CONSTS['verbose']:  print('CTROptimize Retry #{}: Too many peaks...'.format(retry_idx))

            # If the sum of square error metric is to high => Restart
            if err > self.CONSTS['error_threshold']:
                restart = True
                if self.CONSTS['verbose']:  print('CTROptimize Retry #{}: err is too high ({})...'.format(retry_idx,err))

            # Break the loop if we are done
            if not restart:
                break

        if self.CONSTS['verbose']: print('CTROptimize terminated with values {} and err of {}'.format(xopt, err))
            
    def initialize(self, piezo_scan_range=Q_(30,'V'), maxevals=50, initial_current=Q_(220,'mA'), initial_feedforward=Q_(-0.2, 'mA/V'), max_retries =2):
        #Switch the relay position
        
        if self.relay.state[1] != self.CONSTS['ch1_state'] or self.relay.state[4] != self.CONSTS['ch4_state']:
            self.relay.state[1] = self.CONSTS['ch1_state']
            self.relay.state[4] = self.CONSTS['ch4_state']
            time.sleep(0.5)

        # Setup the laser scan
        piezo_scan_range = piezo_scan_range.to('V').m  #Since the scan amplitude is 1V
        self.dlc.piezo_external_input_factor = piezo_scan_range/2
        self.dlc.scan_amplitude = 2
        self.dlc.piezo_voltage = 70 - piezo_scan_range/2
        self.dlc.scan_offset = 1
        self.dlc.scan_channel = 'A'
        self.dlc.piezo_external_input_signal = 'Fine In 1'
        self.dlc.scan_frequency = Q_(100, 'Hz')

        #Setup the fabry perot
        self.fp.selectivity = 0.1
        self.fp.points = 5000

        #Others
        self.num_peak_threshold = int(0.5*piezo_scan_range)
        self.start_time = time.time()
        self.error_metric = self.CONSTS['error_metric']

    def finalize(self, piezo_scan_range=Q_(30,'V'), maxevals=50, initial_current=Q_(220,'mA'), initial_feedforward=Q_(-0.2, 'mA/V'), max_retries =2):
        #Set to passive mode
        self.fp.active_mode = True
        self.dlc.scan_enabled = False
        self.dlc.piezo_external_input_enabled = False


    @Plot1D
    def error(df, cache):
        return {'peak heigth uniformity metric':[df.time, df.peak_uniformity_err],
                'peak spacing metric':[df.time, df.peak_spacing_err]}

    @Plot1D
    def phase_space_uniformity(df, cache):
        return {} #Here since the formatting is a little tricky, we'll do everything (including the actual plotting) in the PlotFormatUpdate
        # return {'state': [df.current, df.feedforward]}

    @PlotFormatInit(LinePlotWidget, ['phase_space_uniformity'])
    def psu_init(plot):
        plot.xlabel = 'current (mA)'
        plot.ylabel = 'feedfoward (mA/V)'
        plot.plot('state', symbol='o', pen=pg.mkPen(color=(255, 255, 255, 50)))

    @PlotFormatUpdate(LinePlotWidget, ['phase_space_uniformity'])
    def psu_update(plot, df, cache):
        errors = df.peak_uniformity_err
        norm_errors = 2*((errors-np.min(errors))/(np.max(errors)-np.min(errors))-0.5)#Normalize to within [-1,1] range
        symbolBrushs = [pg.mkBrush(color=(255*max(err,0), 255*max(-err,0),0,255)) for err in norm_errors]
        symbolBrushs[-1] = pg.mkBrush(color=(0,0,255,255))

        trace, trace_err = plot.traces['state']
        trace.setData(x=df.current, y=df.feedforward, symbol='o', symbolBrush=symbolBrushs)

    @Plot1D
    def fabry_perot(df, cache):
        return {'fp':    [cache['ts'], cache['trace']], 
                'peaks': [cache['peaks_loc'], cache['peaks_mag']*np.max(cache['trace'])]}

    @PlotFormatInit(LinePlotWidget, ['fabry_perot'])
    def fp_init(plot):
        plot.xlabel = 'time (ms)'
        plot.ylabel = 'signal (V)'
        plot.plot('fp', symbol=None)
        plot.plot('peaks', pen=None, symboleSize=50,symbolBrush=(100, 100, 255, 50))

    
