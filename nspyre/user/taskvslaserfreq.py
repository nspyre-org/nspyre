import numpy as np
import time
from nspyre import *
import traceback

from lantz.drivers.ni.simple_daq import Read_DAQ
from lantz.drivers.toptica import DLC
from lantz.drivers.toptica.highfinesse_ws7 import WS7
from lantz.drivers.thorlabs.fabryperot import FabryPerot
from lantz.drivers.sainsmart.relay import Relay

from nspyre.user.gotolaserfreq import GotoLaserFreq

class Piezo_Exception(Exception):
    pass

class TaskVsLaserFreq(Spyrelet):
    REQUIRED_DEVICES = {
        'dlc': DLC,
        'ws7': WS7,
        'fp': FabryPerot,
        'relay': Relay,
        'daq': Read_DAQ, 
    }

    REQUIRED_SPYRELETS = {
        'goto': GotoLaserFreq,
    }

    PARAMS = {
        'fs':               {'type': range, 'units':'THz'},
        'daq_ch':           {'type': str},
        'time_per_point':   {'type': float, 'units': 's'},
        'fp_selectivity':   {'type': float},
    }

    CONSTS = {
        'ws7_ch': 1,
        'relay_ch': 1,
        'relay_state': False,
        'mhf_size': Q_(10, 'GHz'),
        'dvdf':     Q_(3,'nV/Hz'),
        'verbose': False,
    }

    def read(self, time_per_point):
        if self.ttype == 'CI':
            cnt = self.daq.read(self.tname, 1)[0]
            time.sleep(time_per_point)
            val = self.daq.read(self.tname, 1)[0] - cnt
            return val/time_per_point 
        if self.ttype == 'AI':
            clock_rate = 8000 #This is a hardcoded value since getting the actual clock rate is difficult right now...
            samples = int(time_per_point*clock_rate)
            return np.mean(self.daq.read(self.tname,samples)[0])

    def goto_piezo(self, f, tol=Q_(1,'MHz'), timeout=Q_(5,'s')):
        start_time = time.time()
        piezo_v = self.dlc.piezo_voltage
        while time.time()-start_time < timeout.to('s').m:
            #Calc the piezo correction
            curr_freq = self.ws7.frequency[self.CONSTS['ws7_ch']]
            df = (curr_freq - f).to('GHz')
            if np.abs(df)<tol:#Close enough => return
                return

            #Apply the piezo correction
            dpiezo = (self.CONSTS['dvdf'] * df).to('V')
            piezo_v -= dpiezo
            if not Q_(0, 'V') <= piezo_v <= Q_(140, 'V'):
                # piezo value out of range
                raise Piezo_Exception("Piezo out-of range")
            self.dlc.piezo_voltage = piezo_v
            time.sleep(0.05)

        raise TimeoutError("TaskVsLaserFrequency broad_scan: Could not reach frequency with piezo")

    def is_single_mode(self, retry, fp_selectivity):
        #  Retries protect against false negatives
        for i in range(retry):
            self.fp.active_mode = True
            self.fp.selectivity = fp_selectivity
            self.fp.points = 1000
            self.fp.refresh()

            ts = np.linspace(0, self.fp.period.to('ms').m, self.fp.points)

            self.reg_cache_store(ts=ts, trace=self.fp.trace(), peaks_loc=self.fp.peak_locations(), peaks_mag=self.fp.peak_magnitudes())
            self.acquire(None)
            
            if self.fp.single_mode:
                return True
        return False

    def main(self, fs, daq_ch, time_per_point=Q_(0.5, 's'), fp_selectivity=0.2):

        goto_mot = lambda f: self.call(self.goto, f, tolerance=Q_(3, 'GHz'), retry=3, post_tolerance=Q_(10,'GHz'), ctr_optimize=True, fb_iterations=10, ignore_child_progress=True)
        
        # This is for an upward sweep only
        if fs[-1] < fs[0]:
            raise Exception("Only forward sweep is implemented")

        goto_mot(fs[0]+(self.CONSTS['mhf_size']/2))
        if self.CONSTS['verbose']: print('After motor move', self.ws7.frequency[self.CONSTS['ws7_ch']], self.dlc.piezo_voltage)

        #Main loop
        df = (fs[-1]-fs[0])/len(fs) # This is only a good number for standard sweeps
        for f in self.progress(fs):
            for retry in range(3):
                try: # Try to move the piezo
                    movemotor = False
                    self.goto_piezo(f, tol=np.abs(df), timeout=Q_(5,'s'))
                except (TimeoutError, Piezo_Exception) as e:
                    if self.CONSTS['verbose']: traceback.print_exc()
                    movemotor = True     

                if movemotor or not self.is_single_mode(3, fp_selectivity):    # If we couldn't reach the piezo position or if we are multimode
                    goto_mot(f+(self.CONSTS['mhf_size']/2))                    # Move motor
                    if self.CONSTS['verbose']: print('After motor move', self.ws7.frequency[self.CONSTS['ws7_ch']], self.dlc.piezo_voltage)
                else:
                    break                               # Else get out of the for loop and acquire
            amplitude = self.read(time_per_point.to('s').m)
            current_freq = self.ws7.frequency[self.CONSTS['ws7_ch']]
            self.acquire({
                'target_f': f,
                'f': current_freq,
                'amplitude': amplitude,
                })
            
    def initialize(self, fs, daq_ch, time_per_point=Q_(0.5, 's'), fp_selectivity=0.2):
        self.tname = self.name + '_task'
        self.daq.new_task(self.tname, [daq_ch])
        self.ttype = self.daq.get_task_type(self.tname)
        self.daq.start(self.tname)

        if self.relay.state[self.CONSTS['relay_ch']] != self.CONSTS['relay_state']:
            self.relay.state[self.CONSTS['relay_ch']] = self.CONSTS['relay_state']
            time.sleep(0.5)
        
    def finalize(self, fs, daq_ch, time_per_point=Q_(0.5, 's'), fp_selectivity=0.2):
        self.daq.stop(self.tname)
        self.daq.clear_task(self.tname)
        
    @Plot1D
    def freq_scan(df, cache):
        return {'signal': [df.f, df.amplitude]}

    @PlotFormatInit(LinePlotWidget, ['freq_scan'])
    def freq_scan_init(p):
        p.plot('signal', pen=None)
        p.xlabel = 'Frequency (THz)'
        p.ylabel = 'Signal'

    @Plot1D
    def fabry_perot(df, cache):
        return {'fp':    [cache['ts'], cache['trace']], 
                'peaks': [cache['peaks_loc'], cache['peaks_mag']*np.max(cache['trace'])]}

    @PlotFormatInit(LinePlotWidget, ['fabry_perot'])
    def fp_init(plot):
        plot.xlabel = 'Time (ms)'
        plot.ylabel = 'Signal (V)'
        plot.plot('fp', symbol=None)
        plot.plot('peaks', pen=None, symboleSize=50,symbolBrush=(100, 100, 255, 50))