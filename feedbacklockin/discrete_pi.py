'''A DiscretePI object acts a PI feedback loop. It is discrete in the sense
that it takes in an input and produces an output everytime "step" is called;
there is no explicit timebase. It can operate on an arbitrary number of
channels in parallel and can disable specific outputs. It also can be set to
take one of its inputs as an offset reference.
'''
import numpy as np


class DiscretePI(object):
    def __init__(self, channels):
        self._channels = channels

        self._errs = np.zeros(channels)
        self._set_points = np.zeros(channels)
        self._ki = 0.0
        self._kp = 0.0
        self._enabled_outputs = np.zeros(channels, dtype=bool)
        self._input_reference = None

    def set_ki(self, ki):
        self._ki = ki

    def set_kp(self, kp):
        self._kp = kp

    def set_reference(self, channel):
        # Sets the index of the channel being used as a reference.
        # If None, the reference value is zero.
        self._input_reference = channel

    def set_setpoint(self, value, channel):
        self._set_points[channel] = value

    def step(self, inputs):
        """Performs one step of the PI loop."""
        if self._input_reference is not None:
            inputs = inputs - inputs[self._input_reference]

        # Calculate errors.
        err = self._set_points - inputs
        self._errs += err * self._ki

        # Maintains zeroed out error if channels are disabled.
        self._errs = np.multiply(self._errs, self._enabled_outputs)

        return err * self._kp + self._errs

    def zero_errors(self, errors=None):
        # Resets integral errors to assume the proportional error is zero.
        # This is valuable if you discontinuously change the physical
        # system and want let it smoothly find a new equilibrium.
        self._errs = errors

    def set_output_enabled(self, channel, enabled):
        self._enabled_outputs[channel] = enabled
