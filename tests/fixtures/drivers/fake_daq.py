from lantz.core import Driver, Feat, DictFeat

DIN_KEYS = range(1, 10)
DOUT_KEYS = range(1, 10)

class FakeDAQ(Driver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._din = {k : False for k in DIN_KEYS}
        self._dout = {k : False for k in DOUT_KEYS}

    @DictFeat(values={True, False}, keys=list(DOUT_KEYS))
    def dout(self, key):
        return self._dout[key]

    @dout.setter
    def dout(self, key, value):
        self._dout[key] = value

    @DictFeat(values={True: '1', False: '0'}, keys=list(DIN_KEYS))
    def din(self, key):
        return self._din[key]
