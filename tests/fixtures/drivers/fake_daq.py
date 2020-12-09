from lantz.core import Driver, Feat, DictFeat

DIN_KEYS = range(1, 10)
DOUT_KEYS = range(1, 10)

AIN_KEYS = range(1, 10)
AOUT_KEYS = range(1, 10)

class FakeDAQ(Driver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._din = {k : False for k in DIN_KEYS}
        self._dout = {k : False for k in DOUT_KEYS}
        self._ain = {k : 0.0 for k in AIN_KEYS}
        self._aout = {k : 0.0 for k in AOUT_KEYS}

    # digital input
    @DictFeat(values={True, False}, keys=list(DIN_KEYS))
    def din(self, key):
        return self._din[key]
    def reset_din(self, val):
        self._din = {k : val for k in DIN_KEYS}
    def toggle_din(self, key):
        self._din[key] = not self._din[key]

    # digital output
    @DictFeat(values={True, False}, keys=list(DOUT_KEYS))
    def dout(self, key):
        return self._dout[key]
    @dout.setter
    def dout(self, key, value):
        self._dout[key] = value

    # analog input
    @DictFeat(units='V', keys=list(AIN_KEYS))
    def ain(self, key):
        return self._ain[key]

    # analog output
    @DictFeat(units='V', keys=list(AIN_KEYS))
    def aout(self, key):
        return self._aout[key]
    @dout.setter
    def aout(self, key, value):
        self._aout[key] = value
