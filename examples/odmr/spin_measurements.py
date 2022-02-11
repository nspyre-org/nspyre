"""
This is example script demonstrates most of the basic functionality of nspyre.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import time

import numpy as np
from nspyre import DataSource
from nspyre import InstrumentGateway


class SpinMeasurements:
    """Perform spin measurements."""

    def odmr_sweep(self, start: float, stop: float, num_points: int):
        """Run an ODMR (optically detected magnetic resonance) PL (photoluminescence) sweep over a set of microwave frequencies.
        Args:
            start (float): start frequency
            stop (float): stop frequency
            num_points (int): number of points between start-stop (inclusive)
        """

        # connect to the instrument server
        # connect to the data server and create a data set, or connect to an
        # existing one with the same name if it was created earlier.
        with InstrumentGateway() as gw, DataSource('ODMR') as odmr_data:
            # frequencies that will be swept over in the ODMR measurement
            frequencies = np.linspace(start, stop, num_points)

            # photon counts corresponding to each frequency
            counts = np.zeros(num_points)

            # set the signal generator amplitude for the scan (dBm).
            gw.sg.set_amplitude(6.5)

            # sweep counts vs. frequency.
            for i, f in enumerate(frequencies):
                # access the signal generator driver on the instrument server and set its frequency.
                gw.sg.set_frequency(f)
                # wait for counts to accumulate.
                time.sleep(0.1)
                # read the number of photon counts received by the DAQ.
                counts[i] = gw.daq.cnts(1)
                # save the current data to the data server.
                odmr_data.push({'freqs': frequencies, 'counts': counts, 'idx': i})
