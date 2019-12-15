import numpy as np
import time
from nspyre import *
from itertools import count
import traceback

from nspyre.user.ctroptimize import CTROptimize
from nspyre.user.laserfeedback import LaserFeedback

from lantz.drivers.toptica import DLC, MotDLpro
from lantz.drivers.toptica.highfinesse_ws7 import WS7

c = Q_(299792458, 'm/s')

class GotoLaserFreq(Spyrelet):
    REQUIRED_DEVICES = {
        'dlc': DLC,
        'mot': MotDLpro,
        'ws7': WS7
    }

    REQUIRED_SPYRELETS = {
        'ctropt': CTROptimize,
        'laser_fb':LaserFeedback,
    }

    PARAMS = {
        'freq':             {'type': float, 'units':'GHz'},
        'tolerance':        {'type': float, 'units':'GHz'},
        'post_tolerance':   {'type': float, 'units':'GHz'},
        'retry':            {'type': int },
        'ctr_optimize':     {'type': bool},
        'fb_iterations':    {'type': int },

    }

    CONSTS = {
        'ws7_ch': 1,
        'current': Q_(250,'mA')
    }

    def main(self, freq, tolerance=Q_(4, 'GHz'), post_tolerance=Q_(6,'GHz'), retry=3, ctr_optimize=True, fb_iterations=15):

        # --------------Helper functions-------------------------------
        p0, p1, p2 = self.mot.p_coeffs
        def get_next_pos():
            curr_wl, curr_step = self.ws7.wavelength[self.CONSTS['ws7_ch']], self.mot.position
            dwl = ((c / freq).to('nm') - curr_wl).to('nm').m
            dstep = (p1+2*p2*curr_wl.to('nm').m)*dwl #This uses the derivative of the wl to step function (p0+p1*x+p2*x**2)
            return curr_step + dstep

        get_error = lambda: self.ws7.frequency[self.CONSTS['ws7_ch']] - freq
        is_close_to_target = lambda tol: np.abs(get_error().to('GHz').m) < tol
        #--------------------------------------------------------------

        self.at_pos = False
        for retry in self.progress(range(retry)):

            # Iteration by stepping in the direction of target
            for i in self.progress(range(20)):
                try:
                    if not is_close_to_target(tol=tolerance.to('GHz').m): #We should be able to hit ~2GHz
                        # Go to the next position
                        self.mot.position = get_next_pos()
                        time.sleep(0.1)
                        values = {
                            'iteration': i+1,
                            'error': get_error().to('GHz').m,
                            'mot_position': self.mot.position,
                        }
                        self.acquire(values)
                    else:
                        self.acquire(None) #Give control back (to allow for asynchronous stops)
                        break
                except Exception as err:
                    print("GotoFrequency step failed...  Attempting to bring the motor to the target using internal calibration")
                    traceback.print_tb(err.__traceback__)
                    self.mot.wavelength = (c / freq).to('nm')
                    self.acquire(None) #Give control back (to allow for asynchronous stops)
                    

            if is_close_to_target(tol=post_tolerance.to('GHz').m):
                if ctr_optimize:
                    self.call(self.ctropt, initial_current=self.CONSTS['current'])
                    self.acquire(None) #Give control back (to allow for asynchronous stops)
                if fb_iterations:
                    self.call(self.laser_fb, freq=freq, continuous=False, fb_period=Q_(0.1, 's'), num_of_period=fb_iterations)
                    self.acquire(None) #Give control back (to allow for asynchronous stops)

                if is_close_to_target(tol=post_tolerance.to('GHz').m):
                    return
                else:
                    print("GOTOFREQUENCY: Out of range after post-process.  delta_frequency={}GHz".format(get_error().to('GHz').m))
        raise Exception("GotoFrequency did not converge")

    def initialize(self, freq, tolerance=Q_(4, 'GHz'), post_tolerance=Q_(6,'GHz'), retry=3, ctr_optimize=True, fb_iterations=15):
        #Set some resonable values for the piezo voltage and current
        self.dlc.piezo_voltage = Q_(70, 'V')
        self.dlc.current = self.CONSTS['current']

    def finalize(self, freq, tolerance=Q_(4, 'GHz'), post_tolerance=Q_(6,'GHz'), retry=3, ctr_optimize=True, fb_iterations=15):
        pass
        
    @Plot1D
    def freq_error(df, cache):
        return {'Error':[df.iteration, df.error]}

    @PlotFormatInit(LinePlotWidget, ['freq_error'])
    def init_freq_error(p):
        p.xlabel = 'Iteration'
        p.ylabel = 'Error (GHz)'