class FakeSigGen:
    def __init__(self):
        self._amplitude = 0.0
        self._frequency = 1e3
        self._output_en = False
        self._waveform = 'sine'

    def output_enabled(self):
        return self._output_en

    def set_output_enabled(self, value: bool):
        self._output_en = value

    def waveform(self):
        return self._waveform

    def set_waveform(self, value):
        self._waveform = value

    def frequency(self):
        return self._frequency

    def set_frequency(self, value: float):
        self._frequency = value

    def amplitude(self):
        return self._amplitude

    def set_amplitude(self, value: float):
        self._amplitude = value

    def calibrate(self):
        print('sig-gen calibration succeeded')
