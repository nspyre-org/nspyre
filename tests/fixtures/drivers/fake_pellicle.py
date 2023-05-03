class FakePellicle:
    def __init__(self):
        self._state = False

    def state(self):
        return self._state

    def set_state(self, value: bool):
        self._state = value
