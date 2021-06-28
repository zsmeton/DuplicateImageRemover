class Progress:
    def __init__(self, current=0, max_amount=100):
        self._current = 0
        self._max = 100
        # Set max before current to avoid current getting set out of bounds before max is increased
        self.max = max_amount
        self.current = current

    @property
    def max(self):
        return self._max

    @max.setter
    def max(self, max):
        # TODO: add type check
        # Error checks
        if max < 0:
            raise ValueError(f"Cannot set max to less than 0 {max}")
        if self.current > max:
            raise ValueError(f"Cannot set max {max} to less than current {self.current}")
        # Set it
        self._max = max

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, current):
        # TODO: add type check
        if self.max >= current >= 0:
            self._current = current
        else:
            raise ValueError(f"Cannot set current value greater than max {self.max} or less than 0")
