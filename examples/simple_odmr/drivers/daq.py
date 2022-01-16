"""
Fake data acquisition system driver for demonstration purposes.

Author: Jacob Feder
Date: 12/27/2021
"""
import logging
import random

logger = logging.getLogger(__name__)


class DAQ:
    def cnts(self, key):
        """Return the number of counts received."""
        return random.randint(0, 5000)
