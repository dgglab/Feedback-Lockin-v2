import numpy as np

'''
sinOutputs.py makes a sinOutputs object that can emit an array of
sine curves with individual amplitudes (Amps) with a given number
of points in each sine (Npoints).
'''

class sinOutputs:
	
	def __init__(self):
		self.sin_ref  = 0
		self.dataIn   = 0
		self.Npoints  = 1
		self.Nstreams = 1
		self.dataOut  = np.zeros((self.Npoints,self.Nstreams))
		self.Amps     = np.zeros(1)
		self.firstCall = True
		
	def setNpoints(self,N_in):
		#set the number of points in each sine curve
		self.Npoints = N_in
		self.sin_ref = np.sin(2.0*np.pi*np.arange(N_in)/float(N_in))
		self.dataOut = np.zeros((self.Npoints,self.Nstreams))
		
	def setNstreams(self,N_in):
		#sets the number of parallel streams of sine curves
		self.Nstreams = N_in
		self.dataOut = np.zeros((self.Npoints,self.Nstreams))
		self.Amps    = np.zeros(N_in)
	
	def setAmps(self,ampsIn):
		#set the amplitudes of each sine curve
		dataShape = np.shape(ampsIn)
		if dataShape[0] == self.Nstreams:
			self.Amps=ampsIn
			for i in range(self.Nstreams):
				if not np.isnan(ampsIn[i]):
					self.dataOut[:,i] = ampsIn[i]*self.sin_ref
					
	def setSingleAmp(self,ampIn,idx):
		#sets the amplitude of a single sine curve
		self.Amps[idx]=ampIn
		self.dataOut[:,idx] = ampIn*self.sin_ref

	def shiftSingleAmp(self,deltaIn,idx):
		#make a differential change on a single sine curve
		self.Amps[idx]+=deltaIn
		self.dataOut[:,idx] = self.Amps[idx]*self.sin_ref
		
	def output(self):
		#returns the series of sine curves
		return self.dataOut
