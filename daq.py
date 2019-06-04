'''
daq.py defines Daq objects which serve as the low-level
interface to the ni DAQ cards used for continuous reading and writing. It has written-in
connections of external clock signals that are to be hardwired between output and input
DAQ cards. The basic function is that it starts two parallel threads that handle output
and inputs separately. The output DAQ is set-up to only write when its buffer is empty
so that there cannot be a build-up of more than a single cycle delay. The input DAQ takes
its clock signal from the output DAQ and is started first, so that they are synchronized.
Before running this, NI drivers as well as pyDAQmx need to be installed.
TODO(spxtr): Implement this in a less racy manner.
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
        self.data = np.zeros((self._points, self._channels))
        self.dataOut = np.zeros((self._points, self._channels))

    def set_clocks(self, oc, occhan, icchan):
        self.outputClock = oc
        self.outputClockChannel = occhan
        self.inputClockChannel = icchan

    def set_frequency(self, freq):
        self.frequency = freq
        self.rate = self.frequency * self._points

    def set_channels(self, channels_in, channels_out):
        self.channelIn = channels_in
        self.channelOut = channels_out

    def init_daq(self):
        self.inputTaskHandle = mx.TaskHandle()
        self.outputTaskHandle = mx.TaskHandle()
        self.read = c_int32()
        self.written = c_int32()

        self.data = np.zeros((self._points, self._channels), dtype=np.float64)

        self.dataOut = np.zeros((self._points, self._channels), dtype=np.float64)
        self.tempData = np.zeros(self._points * (self._channels + 1),
                dtype=np.float64)
        try:
            # DAQmx Configure Code, Output
            mx.DAQmxConnectTerms(self.outputClock,
                    self.outputClockChannel,
                    mx.DAQmx_Val_DoNotInvertPolarity)
            mx.DAQmxCreateTask("", byref(self.outputTaskHandle))
            mx.DAQmxCreateAOVoltageChan(self.outputTaskHandle,
                    self.channelOut, "", -10.0, 10.0, mx.DAQmx_Val_Volts, None)
            mx.DAQmxSetAODataXferReqCond(self.outputTaskHandle, "" ,
                    mx.DAQmx_Val_OnBrdMemEmpty)
            mx.DAQmxCfgSampClkTiming(self.outputTaskHandle,
                    "OnboardClock", self.rate,mx.DAQmx_Val_Rising,
                    mx.DAQmx_Val_ContSamps, self._points)

            # DAQmx Configure Code, Input
            mx.DAQmxCreateTask("", byref(self.inputTaskHandle))
            mx.DAQmxAddGlobalChansToTask(self.inputTaskHandle, self.channelIn)
            mx.DAQmxCfgSampClkTiming(self.inputTaskHandle, self.inputClockChannel,
                    self.rate, mx.DAQmx_Val_Rising, mx.DAQmx_Val_ContSamps,
                    self._points)
            mx.DAQmxSetReadReadAllAvailSamp(self.inputTaskHandle, True)
        except mx.DAQError as err:
            print("DAQmx Error: %s"%err)

    def stop(self):
        pass

    def start(self):
        # DAQmx Start Code
        mx.DAQmxStartTask(self.inputTaskHandle)
        mx.DAQmxWriteAnalogF64(self.outputTaskHandle, self._points, True, 10.0,
                mx.DAQmx_Val_GroupByChannel, self.data,byref(self.written),
                None)

        WriteThread = threading.Thread(target=self.runWriteThread, args=())
        WriteThread.daemon = True
        WriteThread.start()

        ReadThread = threading.Thread(target=self.runReadThread, args=())
        ReadThread.daemon = True
        ReadThread.start()

    def measureDone(self):
        self.data_ready.emit()

    def readIn(self,data):
        self.data = data.astype(np.float64)

    def OutputData(self):
        return self.dataOut

    def runWriteThread(self):
        # infinite loop writing sinewave to buffer everytime the buffer is emptied
        # sends measureDone() command which emits a callback for the GUI to
        while True:
            try:
                d1 = np.reshape(self.data.T, (self._channels * self._points, 1))
                mx.DAQmxWriteAnalogF64(self.outputTaskHandle, self._points,
                        True, 10.0, mx.DAQmx_Val_GroupByChannel,
                        d1,byref(self.written), None)
                self.measureDone()
            except:
                print("failed to write to DAQ")

    def runReadThread(self):
        # infinite loop reading sinewave and updating the dataOut variable
        while True:
            try:
                mx.DAQmxReadAnalogF64(self.inputTaskHandle, self._points, 10.0,
                        mx.DAQmx_Val_GroupByChannel, self.tempData,
                        self._points * (self._channels + 1), byref(self.read),
                        None)
                self.dataOut = np.reshape(self.tempData[self._points:],
                        (self._points, self._channels), order='F')
            except:
                print("failed to read from DAQ")
