import numpy as np
from lantz.core import Action, Driver, Feat

class FakeSigGen(Driver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._amplitude = 0.0
        self._frequency = 1e3

    @Feat(units='Hz')
    def frequency(self):
        return self._frequency
    @frequency.setter
    def frequency(self, value):
        self._frequency = value

    @Feat(units='V')
    def amplitude(self):
        return self._amplitude
    @amplitude.setter
    def amplitude(self, value):
        self._amplitude = value

    @Action()
    def calibrate(self):
        pass