"""
Fake data acquisition system driver.

Author: Jacob Feder
Date: 12/27/2021
"""

import random
import logging

logger = logging.getLogger(__name__)

COUNTER_KEYS = range(1, 4)

class FakeDAQ():
    def __init__(self):
        # digital counters
        self.reset_cnts()

    def cnts(self, key):
        """Return the current value for a digital output."""
        # randomly increment the counters
        for k in COUNTER_KEYS:
            self._cnt[k] += random.randint(0, 500)

        return self._cnt[key]

    def reset_cnts(self):
        """Reset all counters to 0."""
        self._cnt = {}
        for k in COUNTER_KEYS:
            self._cnt[k] = 0
        logger.debug('Reset all DAQ counters')
