from lantz.core import Driver, Feat

class FakePellicle(Driver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._opened = False

    @Feat(values={True, False})
    def opened(self):
        return self._opened

    @opened.setter
    def opened(self, value):
        self._opened = value
