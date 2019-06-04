"""Perform an exponential moving average over a series of input data.

The only input is the decay constant "a" in units of function calls. Then, each
averaging step is calculated as follows:
    Output(0) = Input(0)
    Output(i) = (1/a) * Input(i) + (1 - 1/a) * Output(i - 1)
The input data can be any values that support multiplication and addition,
including numpy arrays, for which all inputs must have the shape.
"""
class MovingAverager:
    '''A MovingAverager object performs a simple exponential moving average.'''
    def __init__(self, averaging=1.0):
        self.set_averaging(averaging)
        self.reset()

    def reset(self):
        self._old_data = None

    def set_averaging(self, averaging):
        """Set the averaging decay constant in units of function calls."""
        self._new_mult = 1.0 / averaging
        self._old_mult = 1 - self._new_mult

    def step(self, data):
        """Perform one averaging step and return the result."""
        if self._old_data is None:
            self._old_data = data
        self._old_data = self._new_mult * data + self._old_mult * self._old_data
        return self._old_data
