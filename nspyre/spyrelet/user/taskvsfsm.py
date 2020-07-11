import numpy as np
import time
from nspyre import *

from lantz.drivers.newport.fsm300 import Read_FSM

class TaskVsFSM(Spyrelet):
    REQUIRED_DEVICES = {
        'fsm': Read_FSM, 
    }

    PARAMS = {
        'xs':               {'type': range, 'units':'um'},
        'ys':               {'type': range, 'units':'um'},
        'daq_ch':           {'type': str},
        'sweeps':           {'type': int, 'positive': True},
        'acq_rate':         {'type': float, 'nonnegative': True, 'units':'Hz'},
        'pts_per_pixel':    {'type': int, 'positive': True},
    }

    CONSTS = {}

    def main(self, xs, ys, daq_ch, sweeps=1, acq_rate=Q_(5000, 'Hz'), pts_per_pixel=10):
        for sweep in self.progress(range(sweeps)):
            backward = False
            for column_idx, y in enumerate(self.progress(ys.to('um').m)):
                pt0, pt1 = (xs[0].to('um').m, y), (xs[-1].to('um').m, y)
                if backward:
                    pt0, pt1 = pt1, pt0
                row_data = self.fsm.line_scan(init_point=pt0, final_point=pt1, steps=len(xs), acq_rate=acq_rate, pts_per_pos=pts_per_pixel)
                if backward:
                    row_data = np.flip(row_data)
                self.acquire({
                    'sweep_idx': sweep,
                    'column_idx': column_idx,
                    'row_data': row_data,
                    'y':y,
                    'x_vals': xs.to('um').m
                })
                backward = not backward

            
    def initialize(self, xs, ys, daq_ch, sweeps=1, acq_rate=Q_(5000, 'Hz'), pts_per_pixel=10):
        self.fsm.new_input_task([daq_ch])
        
    def finalize(self, xs, ys, daq_ch, sweeps=1, acq_rate=Q_(5000, 'Hz'), pts_per_pixel=10):
        pass

    @PlotFormatInit(HeatmapPlotWidget, ['latest', 'avg'])
    def init_format(p):
        p.xlabel = 'X (um)'
        p.ylabel = 'Y (um)'

    @PlotFormatUpdate(HeatmapPlotWidget, ['latest', 'avg'])
    def update_format(p, df, cache):
        xs, ys     = df.x_vals[0],    df.y.unique()
        diff       = [xs[-1]-xs[0] , ys[-1]-ys[0]]
        p.im_pos   = [np.mean(xs) - diff[0]/2 , np.mean(ys) - diff[1]/2]
        p.im_scale = [diff[0]/len(xs) , diff[1]/len(ys)]
        p.set(p.w.image) #We have to redraw for the scaling to take effect

    @Plot2D
    def latest(df, cache):
        latest = df[df.sweep_idx == df.sweep_idx.max()]
        im = np.vstack(latest.sort_values('column_idx')['row_data'])
        max_rows = len(df.x_vals[0])
        return np.pad(im, (0, max_rows - im.shape[1]), mode='constant', constant_values=0)

    @Plot2D
    def avg(df, cache):
        grouped = df.groupby('column_idx')['row_data']
        averaged = grouped.apply(lambda column: np.mean(np.vstack(column), axis=0))
        im = np.vstack(averaged)
        max_rows = len(df.x_vals[0])
        return np.pad(im, (0, max_rows - im.shape[1]), mode='constant', constant_values=0)