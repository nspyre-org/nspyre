from lantz.core import Action, Driver, Feat


class FakeSigGen(Driver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._amplitude = 0.0
        self._frequency = 1e3
        self._output_en = False
        self._waveform = 0

    @Feat(values={True, False})
    def output_enabled(self):
        return self._output_en

    @output_enabled.setter
    def output_enabled(self, value):
        self._output_en = value

    @Feat(values={'sine': 0, 'square': 1})
    def waveform(self):
        return self._waveform

    @waveform.setter
    def waveform(self, value):
        self._waveform = value

    @Feat(units='Hz', limits=(1, 10e9))
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, value):
        self._frequency = value

    @Feat(units='V', limits=(0, 10))
    def amplitude(self):
        return self._amplitude

    @amplitude.setter
    def amplitude(self, value):
        self._amplitude = value

    @Action()
    def calibrate(self):
        print('sig-gen calibration succeeded')
