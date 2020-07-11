import numpy as np
import time
from nspyre import *
from scipy import optimize

from lantz.drivers.newport.fsm300 import Read_FSM
import traceback

from nspyre.colors import colors

def gaussian(xs, a=1, x0=0, width=1, b=0):
    return a * np.exp(-np.square((xs - x0) / width)) + b

class SpatialFeedback(Spyrelet):
    REQUIRED_DEVICES = {
        'fsm': Read_FSM, 
    }

    PARAMS = {
        'x':               {'type': float, 'units':'um'},
        'y':               {'type': float, 'units':'um'},
        'daq_ch':          {'type': str},
        'iterations':      {'type': int, 'positive': True},
        'x_range':         {'type': float, 'units':'um', 'positive': True},
        'y_range':         {'type': float, 'units':'um', 'positive': True},
        'steps':           {'type': int, 'positive': True},
        'time_per_point':  {'type': float, 'positive': True, 'units':'s'},
    }

    CONSTS = {
        'acq_rate': Q_(20, 'kHz'),
        'max_x_range': Q_(10, 'um'),
        'max_y_range': Q_(10, 'um'),

    }

    def main(self, x, y, daq_ch, iterations=3, x_range=Q_(1.5, 'um'), y_range=Q_(1.5, 'um'), steps= 100, time_per_point=Q_(0.01, 's')):
        max_range = {'x': [x-self.CONSTS['max_x_range'], x+self.CONSTS['max_x_range']],
                     'y': [y-self.CONSTS['max_y_range'], y+self.CONSTS['max_y_range']]}
        pts_per_pos = int(time_per_point*self.CONSTS['acq_rate'])
        def scan_and_fit(pt0, pt1, center, _range, num_steps, axis):
            scan_steps = np.linspace((center - _range).to('um').m, (center + _range).to('um').m, num_steps)
            data = self.fsm.line_scan(init_point=pt0, final_point=pt1, steps=num_steps, acq_rate=self.CONSTS['acq_rate'], pts_per_pos=pts_per_pos)
            p0 = [np.max(data), scan_steps[np.argmax(data)] , 1, np.min(data)]
            popt, pcov = optimize.curve_fit(gaussian, scan_steps, data, p0=p0)
            return {axis+'_steps':scan_steps, axis+'_data':data, axis+'_fit':popt}

        for iteration in self.progress(range(iterations)):
            vals = {'iteration': iteration}
            try:
                vals.update(scan_and_fit((x-x_range, y), (x+x_range, y), x, x_range, steps, 'x'))
                vals.update(scan_and_fit((x, y-y_range), (x, y+y_range), y, y_range, steps, 'y'))
                pos = [Q_(vals['x_fit'][1], 'um'), Q_(vals['y_fit'][1], 'um')]

                # Check if peak is within 1.2*range (to allow for edge fits)
                valid_pos = (x-1.2*x_range)<pos[0]<(x+1.2*x_range) and (y-1.2*y_range)<pos[1]<(y+1.2*y_range)
                # Check if peak is within the max_range
                valid_pos &= max_range['x'][0]<pos[0]<max_range['x'][1] and max_range['y'][0]<pos[1]<max_range['y'][1]
                if valid_pos: 
                    self.fsm.set_position(pos[0], pos[1])
                    self.acquire(vals)
                    x, y = pos
                else:
                    print("Fitted position at {}. Falls outside the range".format(pos))
            except RuntimeError:
                traceback.print_exc()
                continue

            
            
     
    def initialize(self, x, y, daq_ch, iterations=3, x_range=Q_(1.5, 'um'), y_range=Q_(1.5, 'um'), steps= 100, time_per_point=Q_(0.01, 's')):
        self.fsm.new_input_task([daq_ch])
        
    def finalize(self, x, y, daq_ch, iterations=3, x_range=Q_(1.5, 'um'), y_range=Q_(1.5, 'um'), steps= 100, time_per_point=Q_(0.01, 's')):
        pass

    @Plot1D
    def x_scan(df, cache):
        gauss = lambda xs, a, x0, width, b: a * np.exp(-np.square((xs - x0) / width)) + b
        pos = np.array(df.tail(1).x_steps[0])
        return {'data': [pos, df.tail(1).x_data[0]],
                'fit': [pos, gauss(pos, *list(df.tail(1).x_fit[0]))]}

    @Plot1D
    def y_scan(df, cache):
        gauss = lambda xs, a, x0, width, b: a * np.exp(-np.square((xs - x0) / width)) + b
        pos = np.array(df.tail(1).y_steps[0])
        return {'data': [pos, df.tail(1).y_data[0]],
                'fit': [pos, gauss(pos, *df.tail(1).y_fit[0])]}

    @PlotFormatInit(LinePlotWidget, ['x_scan', 'y_scan'])
    def init_format(p):
        p.xlabel = 'Position (um)'
        p.ylabel = 'Signal'
        p.plot('data', pen=colors['r'])
        p.plot('fit', symbol=None, pen=colors['g'])