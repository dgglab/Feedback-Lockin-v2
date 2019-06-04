'''
A SinOutputs object emits an array of sine curves with individual amplitudes
with a given number of points in each sine.
'''
import numpy as np


class SinOutputs(object):
    def __init__(self, channels, points):
        self._npoints = points
        self._nchannels = channels
        self._data_out = np.zeros((points, channels))
        self._amps = np.zeros(channels)
        self._sin_ref = np.sin(2.0 * np.pi * np.arange(points) / points)

    def setAmps(self, amps):
        # Set the amplitudes of each sine curve.
        dataShape = np.shape(amps)
        if dataShape[0] == self._nchannels:
            self._amps = amps
            for i in range(self._nchannels):
                if not np.isnan(amps[i]):
                    self._data_out[:,i] = amps[i]*self._sin_ref

    def setSingleAmp(self, amp, idx):
        # Sets the amplitude of a single sine curve.
        self._amps[idx] = amp
        self._data_out[:,idx] = amp * self._sin_ref

    def shiftSingleAmp(self, deltaIn, idx):
        # Make a differential change on a single sine curve.
        self._amps[idx] += deltaIn
        self._data_out[:,idx] = self._amps[idx] * self._sin_ref

    def output(self):
        # Returns the series of sine curves.
        return self._data_out
