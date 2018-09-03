from pyqtgraph.Qt import QtGui, QtCore, USE_PYSIDE, USE_PYQT5
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
from numpy import random
import threading
import time
from transferMatrixModel import transferMatrixModel

'''
dummyDevice.py defines a dummyDevice object. This is meant to mimic the behavior
of a NIboard and a physical resistor network between the outputs and inputs. it 
uses a transferMatrixModel to generate a random resistor network and adds noise to
the output signal to simulate a real device measurement
'''

class dummyDevice(QObject):
	
	#signal for each time data is acquired
	dataAcquired=pyqtSignal()
		
	def __init__(self):
		super().__init__()
		self.Nparam=1
		self.Npoints=1
		self.tmat = transferMatrixModel()
		self.data = np.zeros((1,1))
		self.noiseAmp=0.2
		

		
	def setNparam(self,N_in):
		# sets the number of parameters used in the device
		self.Nparam=N_in
		self.tmat.setNchannel(self.Nparam)
	
	def setRingOutput(self):
		# simulates a ring of resistors
		self.tmat.biasResistorMod(100)
		self.tmat.scale(.01)
		self.tmat.inv()
	
	def setRandomOutput(self):
		# simulates a random matrix of resistors
		self.tmat.randMatrix()
		self.tmat.biasResistorMod(100)
		self.tmat.scale(.01)
		self.tmat.inv()
	
	def readIn(self,data):
		# reads in data and updates Npoints
		self.data=data
		self.Npoints=np.shape(data)[0]
		
	def OutputData(self):
		
		#performs the "physical" measurement and returns
		tmp = self.tmat.xfer(self.data.T)
		return (tmp+
			(random.randn(self.Nparam,self.Npoints)-0.5)*self.noiseAmp).T
		
		

	def measureDone(self):
		# emits a signal that a measurement is complete
		self.dataAcquired.emit()
	
	def initializeDAQ(self):
		pass
		
	def start(self):
		# infinite loop sending measureDone signal every .055 seconds
		
		# sets a background timer to produce the dataAcquired signal periodically
		thread = threading.Thread(target=self.run, args=())
		thread.daemon = True               # Daemonize thread
		thread.start() 
		
	def run(self):
	
		while True:
			time.sleep(.055)
			self.measureDone()