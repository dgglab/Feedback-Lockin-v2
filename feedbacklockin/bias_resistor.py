'''
A BiasResistor object maps "amps" to "outs" in a manner that approximately
conserves current assuming similar valued bias resistors for each input. This
is tied into the  smooth operation of "FeedbackLockin" objects so that feedback
signals do not drastically alter the DC potential of a device.
'''

import numpy as np


class BiasResistor(object):
    def __init__(self, channels):
        self._channels = channels
        self._amps = np.zeros(channels)
        self._outs = np.zeros(channels)
        self.correctionFactor=0.5
        self.disabledVector = np.ones(channels)
        self._update()
        #self.setZeroSum(0.5)
        #self.setZeroSumDissabledAxes(np.ones(len(channels)))

    def setZeroSum(self):
        # Sets a transfer matrix that takes independant signals and forces them
        # to approximate current conservation. A vector (1,0...0) gets mapped to
        # (1,-phi...-phi) where phi is approximately 1/(N-1). The input
        # correctionFactor goes from 0.0 where phi is ideal, to 1.0 where phi=0
        # the correctionFactor allows for a choice to correct for DC errors.
        self.setZeroSumDisabledAxes(np.zeros(self._channels))
        

    def setZeroSumDisabledAxes(self, disabledVector):
        # As above, but removes the inflence of particular elements.
        self.disabledVector=disabledVector
        self._update()
            
    def _update(self):
        #generates the transfer matrix
        N = self._channels - np.sum(self.disabledVector)
        if N > 1:
            self._xfer_mat = (-np.ones((self._channels,self._channels))
                    / (N - 1) * (1.0 - self.correctionFactor))
            for i in range(self._channels):
                if self.disabledVector[i]:
                    self._xfer_mat[i,:] = 0
                    self._xfer_mat[:,i] = 0
                self._xfer_mat[i,i] = 1.0
        else:
            self._xfer_mat = np.eye(self._channels)
            
    def setCorrectionFactor(self,correctionFactor):
        self.correctionFactor=correctionFactor
        self._update()

    def step(self, amps):
        # Performs the transfer matrix operation.
        self._amps = amps
        self._outs = np.dot(self._xfer_mat, amps)
        return self._outs

    def reverse(self):
        # Reverses the tranfer matrix operation. This is called particularly
        # after the transfer matrix has changed in order to prevent
        # discontinuities in the input code.
        self._amps = np.dot(np.linalg.inv(self._xfer_mat), self._outs)
        return self._amps
