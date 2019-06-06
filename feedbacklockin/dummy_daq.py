"""Dummy DAQ card for local dev.

Includes a randomized resistor network with small random phase offsets. Try to
keep this interface in line with the real DAQ card interface.
"""
import time

import numpy as np
from PySide2.QtCore import *

from feedbacklockin.tmm import TransferMatrixModel


class Daq(QObject):

    data_ready = Signal()

    def __init__(self, channels, points):
        QObject.__init__(self)
        self._channels = channels
        self._points = points
        self._data = np.zeros(points)
        self._tmat = TransferMatrixModel(self._channels)
        self._tmat.biasResistorMod(100)
        self._tmat.scale(0.01)
        self._tmat.inv()

        # Add a small random phase lag to each input by shifting each channel's
        # output by a small amount.
        self._rolls = np.random.randint(-points / 100, points / 100,
                                        size=channels)

        self._timer = QTimer()
        # In a real DAQ card we need to do some processing when the timer
        # fires, but here we do not.
        self._timer.timeout.connect(self.data_ready)

    def set_frequency(self, freq):
        self._frequency = freq

    def set_channels(self, ics, ocs):
        pass

    def set_clocks(self, oc, occhan, icchan):
        pass

    def init_daq(self):
        pass

    def stop(self):
        self._timer.stop()

    def set_output(self, data):
        """In a real DAQ, this would output data."""
        self._data = data

    def get_input(self):
        """In a real DAQ, this would read data."""
        xfer = self._tmat.xfer(self._data.T)
        rand = np.random.randn(self._channels, self._points)
        out = (xfer + (rand - 0.5) * 0.2)
        for i in range(self._channels):
            out[i] = np.roll(out[i], self._rolls[i])
        np.clip(out, -10, 10, out=out)
        return out.T

    def start(self):
        self._timer.start(1000.0 / self._frequency)
