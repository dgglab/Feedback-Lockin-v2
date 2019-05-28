from pyqtgraph.Qt import QtGui, QtCore, USE_PYSIDE, USE_PYQT5
import numpy as np

from sinOutputs import sinOutputs
from lockInCalculator import lockInCalculator
from movingAverager import movingAverager
from discretePI import discretePI
from biasResistor import biasResistor

'''
feedbackLockin.py defines a feedbackLockin object, which functions as multi-terminal
lock-in amplifier with feedback to maintain certain setpoints. Its intended function
is to allow for sourcing of current to contacts of a multi-terminal device in order
to conrol the potential at certain nodes. In particular, it can act to set virtual 
grounds in the device and record the current passing into our out of each node.
'''


class feedbackLockin(QtCore.QObject):

	def __init__(self):
		super().__init__()
		self.Nparam=8
		self.Npoints=1000
		self.Kint=.01
		self.Kprop=0
		self.maxOut = 10.0
		self.minOut = -10.0
		###self.offsets = np.zeros(self.Nparam)
		# data variables
		###self.vOuts=np.zeros(self.Nparam)
		###self.vIns=np.zeros(self.Nparam)
		###self.ACins=np.zeros(self.Nparam)
		###self.data=np.zeros((self.Npoints,self.Nparam))
		
		# boolean flag for whether an input is 
		###self.feedBackOn=np.ones(self.Nparam,dtype=bool)
		
		self.controlPI=discretePI()
		###self.controlPI.setNparams(self.Nparam)
		self.controlPI.setKint(self.Kint)
		self.controlPI.setKprop(self.Kprop)
		
		#biasR is used to ensure current conservation, effectively
		#tying feedback loops together
		self.biasR=biasResistor()
		###self.biasR.setNparam(self.Nparam)
		self.biasR.setZeroSum(0.5)
		
		
		#produces the sine waves sent to the bias resistors
		self.sines = sinOutputs()
		self.setNparam(self.Nparam)
		
		###self.setupSines()
		
		#reads out amplitude from AC signal
		self.lockIn1 = lockInCalculator()
		self.lockIn1.setNpoints(self.Npoints)

		#averager 
		self.averager = movingAverager()
		
	def setNparam(self,Nparam_in):
		self.Nparam = Nparam_in
		self.offsets = np.zeros(self.Nparam)
		self.vOuts=np.zeros(self.Nparam)
		self.vIns=np.zeros(self.Nparam)
		self.ACins=np.zeros(self.Nparam)
		self.Phaseins=np.zeros(self.Nparam)
		self.data=np.zeros((self.Npoints,self.Nparam))
		self.feedBackOn=np.ones(self.Nparam,dtype=bool)
		self.controlPI.setNparams(self.Nparam)
		self.biasR.setNparam(self.Nparam)
		self.setupSines()
		
	def setNpoints(self,N_in):
		self.Npoints=N_in
		self.setupSines()
		self.lockIn1.setNpoints(self.Npoints)
		
	def setupSines(self):
		self.sines.setNpoints(self.Npoints)
		self.sines.setNstreams(self.Nparam)
	
	def setLims(self,minLim,maxLim):
		#set the limits on output signal. Clips sine waves
		self.maxOut = maxLim
		self.minOut = minLim
	
	def updateAmps(self,input,idx):
		#updates the Amplitude
		self.sines.setSingleAmp(input,idx)
		self.vOuts[idx]=input
		
	def updateAve(self,input):
		#changes the averaging 
		self.averager.setAveraging(input)
	
	def updateSetpoints(self,input,idx):
		#updates the feedback setpoints
		self.controlPI.updateSingleSetpoint(input,idx)
		self.vIns[idx]=input
	
	def updateFeedback(self,Kint,Kprop):
		#updates the integration and proportional constants
		self.controlPI.setKint(Kint)
		self.controlPI.setKprop(Kprop)
		self.Kint=Kint
		self.Kprop = Kprop

	def disableFeedback(self,idx):
		#turns feedback off
		self.feedBackOn[idx]=False
		self.biasR.setZeroSumDisabledAxes(.5,True-self.feedBackOn)
		self.controlPI.disableOutput(idx)
		self.controlPI.zeroErrors(self.biasR.reverse())
	
	def enableFeedback(self,idx):
		#turns feedback on
		self.feedBackOn[idx]=True
		self.biasR.setZeroSumDisabledAxes(.5,True-self.feedBackOn)

		self.controlPI.enableOutput(idx)
		self.controlPI.zeroErrors(self.biasR.reverse())
	
	def setReference(self,idx):
		#sets the index of the channel being used as a reference
		#if <0 the reference value is zero
		self.controlPI.setReferenceIdx(idx)
	
	def sineOut(self):
		#returns the output data
		outData = self.sines.output()+self.offsets
		if max(np.abs(self.vOuts)+self.offsets)>self.maxOut:
			idxMax = np.where((np.abs(self.vOuts)+self.offsets)==max(np.abs(self.vOuts)+self.offsets))[0][0]
			r = np.squeeze(np.where(np.squeeze(outData[:,idxMax])>self.maxOut))
			for i in range(self.Nparam):
				
				outData[r,i]=self.vOuts[i]/self.vOuts[idxMax]*self.maxOut+self.offsets[i]
		
		if min(-np.abs(self.vOuts)+self.offsets)<self.minOut:
			idxMin = np.where(-(np.abs(self.vOuts)+self.offsets)==min(-np.abs(self.vOuts)+self.offsets))[0][0]
			r = np.squeeze(np.where(np.squeeze(outData[:,idxMin])<self.minOut))
			for i in range(self.Nparam):
				outData[r,i]=self.vOuts[i]/self.vOuts[idxMin]*self.minOut

		return outData
		
	
	def autoTunePID(self,scaleFactor=1):
		try:
			if np.max(np.abs(self.vOuts))>.001:
				ampsRatio=scaleFactor*np.max(np.abs(self.vOuts))/np.max(np.abs(self.vIns))
				self.updateFeedback(ampsRatio,self.Kprop)
		except:
			print("Error in feedbacklockin.autoTunePID")
		
		return ampsRatio
		
	def readIn(self,data):
		#reads data in and preforms feedback step
		
		self.data=data
		
		#Fourier component measured
		ampsReadIn=self.averager.step(self.lockIn1.calcAmps(data.T)[1]) #X
		Y=self.averager.step(self.lockIn1.calcAmps(data.T)[0]) #Y
		PhaseReadIn=np.degrees(np.arctan2(Y,ampsReadIn)) #Phase	
		
		#setpoint amplitudes calculated
		ampsSetOut=self.controlPI.step(ampsReadIn)
		
				#if no feedback, force output to its original value
		for i in range(self.Nparam):
			if not self.feedBackOn[i]:
				ampsSetOut[i]=self.vOuts[i]
				
		#transform to maintain current conservation
		ampsSetOut = self.biasR.step(ampsSetOut)
		
		#updates the output sinewaves
		self.sines.setAmps(ampsSetOut)
		
		
		for i in range(self.Nparam):
			self.ACins[i]=ampsReadIn[i]
			self.Phaseins[i]=PhaseReadIn[i]
			
			if self.feedBackOn[i]:
				
				self.vOuts[i]=ampsSetOut[i]

			
		#print(self.offsets[0])