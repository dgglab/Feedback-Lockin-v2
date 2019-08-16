from PySide2.QtCore import *
import numpy as np

from feedbacklockin.sin_outs import SinOutputs
from feedbacklockin.lockin_calc import LockinCalculator
from feedbacklockin.moving_averager import (NoneAverager,
        ExponentialAverager, SlidingWindowAverager)
from feedbacklockin.discrete_pi import DiscretePI
from feedbacklockin.bias_resistor import BiasResistor


_MIN_OUT = -10.0
_MAX_OUT = 10.0


class FeedbackLockin(QObject):
    def __init__(self, channels, points):
        QObject.__init__(self)
        self._channels = channels

        self._control_pi = DiscretePI(channels)
        self._lockin = LockinCalculator(points)
        self._bias_r = BiasResistor(channels)
        self._sines = SinOutputs(channels, points)

        # Average both the amplitudes as well as the raw input data.
        self._avg_type = 0
        self._averagers = [(NoneAverager(), NoneAverager()),
                (SlidingWindowAverager(), SlidingWindowAverager()),
                (ExponentialAverager(), ExponentialAverager())]
        self._amp_averager, self._series_averager = self._averagers[0] 

        self.vOuts = np.zeros(channels)
        self.vIns = np.zeros(channels)
        self.avged = np.zeros(channels)
        self.Phaseins = np.zeros(channels)
        self._feedback_on = np.zeros(channels)

    def reset_avg(self):
        for a1, a2 in self._averagers:
            a1.reset()
            a2.reset()

    def update_amps(self, val, chan):
        self._sines.setSingleAmp(val, chan)
        self.vOuts[chan] = val

    def update_averaging(self, averaging):
        for a1, a2 in self._averagers:
            a1.set_averaging(averaging)
            a2.set_averaging(averaging)

    def update_setpoint(self, val, chan):
        self._control_pi.set_setpoint(val, chan)
        self.vIns[chan] = val

    def update_k(self, ki, kp):
        self._control_pi.set_ki(ki)
        self._control_pi.set_kp(kp)

    def set_averaging_type(self, avg_type):
        """Options are 0: None, 1: sliding window, and 2: exponential."""
        if avg_type == self._avg_type:
            return
        self._avg_type = avg_type
        self._amp_averager, self._series_averager = self._averagers[avg_type]
        self.reset_avg()

    def set_feedback_enabled(self, chan, enabled):
        enabled_int = 1 if enabled else 0
        self._feedback_on[chan] = enabled_int
        self._bias_r.setZeroSumDisabledAxes(0.5, 1 - self._feedback_on)
        self._control_pi.zero_errors(self._bias_r.reverse())
        self._control_pi.set_output_enabled(chan, enabled_int)

    def set_reference(self, chan):
        self._control_pi.set_reference(chan)

    def sine_out(self):
        out = self._sines.output()
        np.clip(out, _MIN_OUT, _MAX_OUT, out)
        return out

    def autotune_pid(self, scaleFactor):
        if np.max(np.abs(self.vOuts)) > .001:
            ampsRatio = (scaleFactor * np.max(np.abs(self.vOuts))
                / np.max(np.abs(self.avged[0])))
            self._control_pi.set_ki(ampsRatio)
        return ampsRatio

    def read_in(self, data):
        calced_amps = self._lockin.calc_amps(data)
        self.data = self._series_averager.step(data)
        self.avged = self._amp_averager.step(calced_amps)
        X = self.avged[0]
        Y = self.avged[1]
        self.X = X
        self.Y = Y
        self.R = np.sqrt(X*X + Y*Y)
        self.P = np.degrees(np.arctan2(Y, X))

        # Setpoint amplitudes calculated. Note that we feedback on the
        # unaveraged results.
        pi_outs = self._control_pi.step(calced_amps[0])
        amps_out = np.where(self._feedback_on, pi_outs, self.vOuts)

        # Transform to maintain current conservation.
        amps_out = self._bias_r.step(amps_out)

        # Updates the output sinewaves.
        self._sines.setAmps(amps_out)

        self.vOuts = np.where(self._feedback_on, amps_out, self.vOuts)
