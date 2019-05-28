from pyqtgraph.Qt import QtGui, QtCore, USE_PYSIDE, USE_PYQT5
from PyQt5.QtCore import QObject, pyqtSignal
import PyDAQmx as mx
import numpy as np
from ctypes import byref, c_int32

import threading
import time

'''
daqLockInHardware.py defines daqLockInHardware objects which serve as the low-level
interface to the ni DAQ cards used for continuous reading and writing. It has written-in
connections of external clock signals that are to be hardwired between output and input
DAQ cards. The basic function is that it starts two parallel threads that handle output
and inputs separately. The output DAQ is set-up to only write when its buffer is empty
so that there cannot be a build-up of more than a single cycle delay. The input DAQ takes
its clock signal from the output DAQ and is started first, so that they are synchronized.
Before running this, NI drivers as well as pyDAQmx need to be installed.
'''

class daqLockInHardware(QObject):

	#signal for each time data is acquired
	dataAcquired=pyqtSignal()
		
	def __init__(self):
		super().__init__()
		self.Nparam=1
		self.Npoints=1
		self.data = np.zeros((1,1))
		self.dataOut = np.zeros((1,1))
		self.frequency=17.76
		self.rate=1000
				
	def setNparam(self,N_in):
		# sets the number of parameters used in the device
		self.Nparam = N_in
		self.data = np.zeros((self.Npoints,self.Nparam))
		self.dataOut = np.zeros((self.Npoints,self.Nparam))
	
	def setNpoints(self,N_in):
		# sets the number of parameters used in the device
		self.Npoints = N_in
		self.data = np.zeros((self.Npoints,self.Nparam))
		self.dataOut = np.zeros((self.Npoints,self.Nparam))
	
	def setClocks(self,outputClock,outputClockChannel,inputClockChannel):
		self.outputClock=outputClock
		self.outputClockChannel=outputClockChannel
		self.inputClockChannel=inputClockChannel
	
	def setSampleRate(self):
		# sets the sample rate of the DAQ card
		self.rate=self.frequency*self.Npoints
		
	def inputChannels(self,channels_in):
		#sets channelIn string
		self.channelIn = channels_in
	
	def outputChannels(self,channels_out):
		#sets channelOut string
		self.channelOut = channels_out
	
	def initializeDAQ(self):
	
		#initializes the DAQ cards and starts the 
		self.inputTaskHandle = mx.TaskHandle()
		self.outputTaskHandle = mx.TaskHandle()
		self.read = c_int32()
		self.written = c_int32()
		
		self.data = np.zeros((self.Npoints,self.Nparam), dtype=np.float64)
		
		self.dataOut = np.zeros((self.Npoints,self.Nparam), dtype=np.float64)
		self.tempData= np.zeros(self.Npoints*(self.Nparam+1), dtype=np.float64)
		try:
			
			# DAQmx Configure Code, Output
			mx.DAQmxConnectTerms(self.outputClock,self.outputClockChannel,mx.DAQmx_Val_DoNotInvertPolarity)
			mx.DAQmxCreateTask("",byref(self.outputTaskHandle))
			mx.DAQmxCreateAOVoltageChan(self.outputTaskHandle,self.channelOut,"",-10.0,10.0,mx.DAQmx_Val_Volts,None)
			#mx.DAQmxSetWriteRegenMode(self.outputTaskHandle,mx.DAQmx_Val_DoNotAllowRegen)
			mx.DAQmxSetAODataXferReqCond(self.outputTaskHandle,"",mx.DAQmx_Val_OnBrdMemEmpty)
			mx.DAQmxCfgSampClkTiming(self.outputTaskHandle,"OnboardClock",self.rate,mx.DAQmx_Val_Rising,mx.DAQmx_Val_ContSamps,self.Npoints)
			
			# DAQmx Configure Code, Input	
			mx.DAQmxCreateTask("",byref(self.inputTaskHandle))
			#mx.DAQmxCreateAIVoltageChan(self.inputTaskHandle,self.channelIn,"",mx.DAQmx_Val_Cfg_Default,-10.0,10.0,mx.DAQmx_Val_Volts,None)
			mx.DAQmxAddGlobalChansToTask(self.inputTaskHandle,self.channelIn)
			mx.DAQmxCfgSampClkTiming(self.inputTaskHandle,self.inputClockChannel,self.rate,mx.DAQmx_Val_Rising,mx.DAQmx_Val_ContSamps,self.Npoints)
			
			mx.DAQmxSetReadReadAllAvailSamp(self.inputTaskHandle,True)

			

		except mx.DAQError as err:
			print("DAQmx Error: %s"%err)
		
		
		
	def start(self):
		#starts the DAQ tasks andd read and write threads for continuous read/write

		# DAQmx Start Code
		mx.DAQmxStartTask(self.inputTaskHandle)		
		mx.DAQmxWriteAnalogF64(self.outputTaskHandle,self.Npoints,True,10.0,mx.DAQmx_Val_GroupByChannel,self.data,byref(self.written),None)

		WriteThread = threading.Thread(target=self.runWriteThread, args=())
		WriteThread.daemon = True               # Daemonize thread
		WriteThread.start() 
		
		ReadThread = threading.Thread(target=self.runReadThread, args=())
		ReadThread.daemon = True               # Daemonize thread
		ReadThread.start() 
		
	
	def measureDone(self):
		# emits a signal that a measurement is complete
		self.dataAcquired.emit()
		
	def readIn(self,data):
		# reads in data and updates Npoints
		self.data=data.astype(np.float64)
	
	def OutputData(self):
		# outputs internal data
		return self.dataOut
		
	def runWriteThread(self):
		# infinite loop writing sinewave to buffer everytime the buffer is emptied
		# sends measureDone() command which emits a callback for the GUI to 
		while True:	
			try:
				d1=np.reshape(self.data.T,(self.Nparam*self.Npoints,1))
				mx.DAQmxWriteAnalogF64(self.outputTaskHandle,self.Npoints,True,10.0,mx.DAQmx_Val_GroupByChannel,d1,byref(self.written),None)
				self.measureDone()
				#print("written")
			except:
				print("failed to write to DAQ")
				
	def runReadThread(self):
		# infinite loop reading sinewave and updating the dataOut variable
		while True:
			try:
				mx.DAQmxReadAnalogF64(self.inputTaskHandle,self.Npoints,10.0,mx.DAQmx_Val_GroupByChannel,self.tempData,self.Npoints*(self.Nparam+1),byref(self.read),None)
				self.dataOut=np.reshape(self.tempData[self.Npoints:],(self.Npoints,self.Nparam),order='F')
				#print("read")
			except:
				print("failed to read from DAQ")

			