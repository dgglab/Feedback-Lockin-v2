'''
Daq objects serve as the low-level interface to the NI DAQ cards used for
continuous reading and writing. It has written-in connections of external clock
signals that are to be hardwired between output and input DAQ cards. The basic
function is that it starts two parallel threads that handle output and inputs
separately. The output DAQ is set-up to only write when its buffer is empty so
that there cannot be a build-up of more than a single cycle delay. The input
DAQ takes its clock signal from the output DAQ and is started first, so that
they are synchronized.
'''
from ctypes import byref, c_int32
import threading
import time

import numpy as np
import PyDAQmx as mx
from PySide2.QtCore import *


class Daq(QObject):

    data_ready = Signal()

    def __init__(self, channels, points):
        QObject.__init__(self)
        self._channels = channels
        self._points = points

    def set_clocks(self, oc, occhan, icchan):
        self._oc = oc
        self._occhan = occhan
        self._icchan = icchan

    def set_frequency(self, freq):
        self._rate = freq * self._points

    def set_channels(self, channels_in, channels_out):
        self._channels_in = channels_in
        self._channels_out = channels_out

    def init_daq(self):
        self._input_task = mx.TaskHandle()
        self._output_task = mx.TaskHandle()

        mx.DAQmxConnectTerms(self._oc, self._occhan,
                mx.DAQmx_Val_DoNotInvertPolarity)
        mx.DAQmxCreateTask("", byref(self._output_task))
        mx.DAQmxCreateAOVoltageChan(self._output_task, self._channels_out, "",
                -10.0, 10.0, mx.DAQmx_Val_Volts, None)
        mx.DAQmxSetAODataXferReqCond(self._output_task, "",
                mx.DAQmx_Val_OnBrdMemEmpty)
        mx.DAQmxCfgSampClkTiming(self._output_task, "OnboardClock", self._rate,
                mx.DAQmx_Val_Rising, mx.DAQmx_Val_ContSamps, self._points)

        mx.DAQmxCreateTask("", byref(self._input_task))
        mx.DAQmxAddGlobalChansToTask(self._input_task, self._channels_in)
        mx.DAQmxCfgSampClkTiming(self._input_task, self._icchan, self._rate,
                mx.DAQmx_Val_Rising, mx.DAQmx_Val_ContSamps, self._points)
        mx.DAQmxSetReadReadAllAvailSamp(self._input_task, True)

    def stop(self):
        self._write_thread.requestInterruption()
        self._read_thread.requestInterruption()

    def start(self):
        self._write_thread = WriteThread(self._channels, self._points, self._output_task)
        self._write_thread.start()

        self._read_thread = ReadThread(self._channels, self._points, self._input_task)
        self._read_thread.start()

    def set_output(self, data):
        self._write_thread.set_output(data)

    def get_input(self):
        return self._read_thread.get_input()


class WriteThread(QThread):

    data_ready = Signal()

    def __init__(self, channels, points, task):
        QThread.__init__(self)
        self._channels = channels
        self._points = points
        self._output_task = task
        self._written = c_int32()
        self._data_in = np.zeros((points, channels), dtype=np.float64)
        self._mut = QMutex()

    def set_output(self,data):
        with QMutexLocker(self._mut):
            self._data_in = np.copy(data.astype(np.float64))

    def run(self):
        with QMutexLocker(self._mut):
            mx.DAQmxWriteAnalogF64(self._output_task, self._points, True, 10.0,
                mx.DAQmx_Val_GroupByChannel, self._data_in, byref(self._written),
                None)

        while not self.isInterruptionRequested():
            with QMutexLocker(self._mut):
                d_copy = np.copy(self._data_in)
            d = np.reshape(d_copy.T, (self._channels * self._points, 1))
            mx.DAQmxWriteAnalogF64(self._output_task, self._points,
                    True, 10.0, mx.DAQmx_Val_GroupByChannel,
                    d, byref(self._written), None)
            self.data_ready.emit()


class ReadThread(QThread):
    def __init__(self, channels, points, task):
        QThread.__init__(self)
        self._channels = channels
        self._points = points
        self._output_task = task
        self._read = c_int32()
        self._data_out = np.zeros((points, channels), dtype=np.float64)
        self._mut = QMutex()

    def get_input(self):
        with QMutexLocker(self._mut):
            return np.copy(self._data_out)

    def run(self):
        mx.DAQmxStartTask(self._input_task)
        temp_data = np.zeros(self._points * (self._channels + 1), dtype=np.float64)
        while not self.isInterruptionRequested():
            mx.DAQmxReadAnalogF64(self._input_task, self._points, 10.0,
                    mx.DAQmx_Val_GroupByChannel, temp_data,
                    self._points * (self._channels + 1), byref(self._read),
                    None)
            with QMutexLocker(self._mut):
                self._data_out = np.reshape(temp_data[self._points:],
                    (self._points, self._channels), order='F')
