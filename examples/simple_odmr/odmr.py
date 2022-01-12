"""
This is example script demonstrates most of the basic functionality of nspyre.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import time

import numpy as np
from nspyre import DataSink
from nspyre import DataSource
from nspyre import LinePlotWidget


class ODMR:
    def __init__(self, sg, daq):
        """For running an ODMR (optically detected magnetic resonance) PL (photoluminescence) scan"""
        # signal generator
        self.sg = sg
        # data acquisition system
        self.daq = daq

    def sweep(self, start: float, stop: float, num_points: int) -> np.ndarray:
        """Run an ODMR sweep over a set of frequencies.
        Args:
            start (float): start frequency
            stop (float): stop frequency
            num_points (int): number of points between start-stop (inclusive)
        """

        # connect to the data server and create a data set, or connect to an
        # existing one with the same name if it was created earlier
        with DataSource('ODMR') as odmr_data:
            # frequencies that will be swept over in the ODMR measurement
            frequencies = np.linspace(start, stop, num_points)
            odmr_data.add('freqs', frequencies)

            # photon counts corresponding to each frequency
            counts = np.zeros(num_points)
            odmr_data.add('counts', counts)

            # sig gen amplitude for the scan (dBm)
            self.sg.set_amplitude = 6.5

            # sweep counts vs frequency
            for i, f in enumerate(frequencies):
                # access the signal generator driver on the instrument server and set its frequency
                self.sg.set_frequency(f)
                # wait for counts to accumulate
                time.sleep(1)
                # read the number of photon counts received by the DAQ
                counts[i] = self.daq.cnts(1)
                # save the current data to the data server
                odmr_data.update()

    # TODO save()


class ODMRPlotWidget(LinePlotWidget):
    def setup(self):
        self.new_plot('ODMR')
        self.plot_widget.setYRange(-3, 3)
        self.sink = DataSink('ODMR')

    def update(self):
        self.sink.update()
        print(f'f: {self.sink.freqs} c: {self.sink.counts}')
        self.set_data('ODMR', self.sink.freqs, self.sink.counts)
        # f = np.linspace(0, 1000, num=1000)
        # c1 = np.random.normal(size=len(f))
        # c2 = np.random.normal(size=len(f))
        # self.set_data('ODMR+', f, c1)
        # self.set_data('ODMR-', f, c2)
