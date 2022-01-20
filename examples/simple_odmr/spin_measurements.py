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

        # Connect to the instrument server.
        # Connect to the data server and create a data set, or connect to an
        # existing one with the same name if it was created earlier.
        with InstrumentGateway() as gw, DataSource('ODMR') as odmr_data:
            # Frequencies that will be swept over in the ODMR measurement
            frequencies = np.linspace(start, stop, num_points)

            # Photon counts corresponding to each frequency
            counts = np.zeros(num_points)

            # Set the signal generator amplitude for the scan (dBm).
            gw.sg.set_amplitude(6.5)

            # Sweep counts vs. frequency.
            for i, f in enumerate(frequencies):
                # Access the signal generator driver on the instrument server and set its frequency.
                gw.sg.set_frequency(f)
                # Wait for counts to accumulate.
                time.sleep(0.5)
                # Read the number of photon counts received by the DAQ.
                counts[i] = gw.daq.cnts(1)
                # Save the current data to the data server.
                odmr_data.push({'freqs': frequencies, 'counts': counts})

    # TODO save()
