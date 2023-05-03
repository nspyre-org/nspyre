class FakeDAQ:
    def __init__(self):
        self._dout = {}
        for k in range(10):
            self._dout[k] = False

        self._aout = {}
        for k in range(10):
            self._aout[k] = 0.0

    # digital input (assuming they're connected to corresponding dout pins)
    def din(self, key: int):
        return self._dout[key]

    # digital output
    def dout(self, key: int, value: bool):
        self._dout[key] = value

    # analog input (assuming they're connected to corresponding aout pins)
    def ain(self, key: int):
        return self._aout[key]

    # analog output
    def aout(self, key: int, value: float):
        self._aout[key] = value
