'''
Computes the in and out-of-phase components (X and Y) of an input signal.

Lockin amplifiers rely on the fact that sines and cosines of differing
frequencies are orthogonal. Thus, if we multiply a long timeseries with a sine
or cosine at a particular frequency, we will pick out only the Fourier
component of the series at that frequency.
'''
import numpy as np


class LockinCalculator:
    """LockinCalculator computes the X and Y components of a signal.

    points is the number of points per period of oscillation.
    """
    def __init__(self, points):
        self.set_points(points)

    def set_points(self, points):
        """(Re)set the number of points per oscillation."""
        sin_ref = np.sin(np.linspace(0, 2 * np.pi, points))
        cos_ref = np.cos(np.linspace(0, 2 * np.pi, points))

        sin_ref /= np.sum(sin_ref ** 2)
        cos_ref /= np.sum(cos_ref ** 2)

        self._ref = np.vstack((sin_ref, cos_ref))

    def calc_amps(self, data):
        """Multiply the reference curves by the data.

        The reference curves are a 2 x (points) array (X and Y), so the input
        data must be (points) x (channels).
        The result will then be 2 x (channels).
        """
        return np.matmul(self._ref, data)
