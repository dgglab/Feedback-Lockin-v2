'''
A TransferMatrixModel is a general transfer matrix object that can store an
arbirary NxN matrix and perform matrix multiplication on an N element vector.
It particularly has built-in functions for creating model
conductance/resistance matrices to simulate the outputs of a given multi-
terminal device
'''

import numpy as np


class TransferMatrixModel(object):
    def __init__(self, channels):
        self._nchannels = channels
        self.makeRing()
        self.firstCall = True

    def randMatrix(self):
        # Produces a viable, random conductance matrix.
        self._xfer_matrix = np.random.rand(self._nchannels, self._nchannels) / 2.0
        self._xfer_matrix = -np.dot(self._xfer_matrix.T, self._xfer_matrix)
        # Ensures that DC offsets do not change the output.
        self.zeroOutRows()

    def symmetrize(self):
        # Symmetrizes the transfer matrix.
        self._xfer_matrix = (self._xfer_matrix + self._xfer_matrix.T) / 2.0

    def antisymmetrize(self):
        # Antisymmetrizes the transfer matrix.
        self._xfer_matrix = (self._xfer_matrix - self._xfer_matrix.T) / 2.0

    def zeroOutRows(self):
        # Makes diagonal elements equal to the negative of all other
        # elements in a row. This ensures that the eigenvector (1,1,...,1)
        # has an eigenvalue of zero, meaning that DC offsets in voltage
        # would not produce a change in current.
        for i in range(self._nchannels):
            self._xfer_matrix[i,i] -= np.sum(self._xfer_matrix[i,:])

    def makeRing(self):
        # Models a ring of resistors in transfer matrix.
        self._xfer_matrix = np.zeros((self._nchannels, self._nchannels))
        for i in range(self._nchannels - 1):
            self._xfer_matrix[i, i+1] = -0.5
            self._xfer_matrix[i+1, i] = -0.5
            self._xfer_matrix[i, i]   = 1.0
        self._xfer_matrix[-1, -1] = 1.0
        self._xfer_matrix[0, -1]  = -.5
        self._xfer_matrix[-1, 0]  = -.5

    def xfer(self, data):
        # Performs matrix multiplcation.
        return np.dot(self._xfer_matrix, data)

    def biasResistorMod(self, R):
        # Modifies the transfer matrix to presume you have the sitution
        # GV=I=(Vout-V)/R so that it transfers from (R G+1)V=Vout.
        self._xfer_matrix = R * self._xfer_matrix + np.eye(self._nchannels)

    def inv(self):
        # Inverts internal transfer matrix.
        self._xfer_matrix = np.linalg.inv(self._xfer_matrix)

    def scale(self,scaleFactor):
        # Scales internal transfer matrix.
        self._xfer_matrix *= scaleFactor
