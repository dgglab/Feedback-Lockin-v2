import numpy as np

'''
biasResistor.py creates a biasResistor object. The main function of the object
is to map "Amps_in" to "outs" in a manner that approximately conserves current
assuming similar valued bias resistors for each input. This is tied into the 
smooth operation of "feedbackLockIn" objects so that feedback signals do not 
drastically alter the DC potential of a device. 
'''

class biasResistor:

	def __init__(self):
		self.N=1
		self.Amps=np.zeros(1)
		self.outs=np.zeros(1)
		self.xferMat=np.ones((1,1))
		
		
	def setNparam(self,N_in):
		#sets the number of elements to transform
		self.N=N_in
		self.Amps=np.zeros(N_in)
		self.outs=np.zeros(N_in)
		self.setZeroSum(.01)

		
	def setZeroSum(self,correctionFactor):
		# sets a transfer matrix that takes independant signals and forces them
		# to approximate current conservation. A vector (1,0...0) gets mapped to
		# (1,-phi...-phi) where phi is approximately 1/(N-1). The input 
		# correctionFactor goes from 0.0 where phi is ideal, to 1.0 where phi=0
		# the correctionFactor allows for a choice to correct for DC errors
		self.xferMat=-np.ones((self.N,self.N))/(self.N-1)*(1.0-correctionFactor)
		for i in range(self.N):
			self.xferMat[i,i]=1.
			
			
	def setZeroSumDisabledAxes(self,correctionFactor,disabledVector):
		# as above, but removes the inflence of particular elements
		N=self.N-np.sum(disabledVector)
		if N>1:
			self.xferMat=-np.ones((self.N,self.N))/(N-1)*(1.0-correctionFactor)
			for i in range(self.N):
				if disabledVector[i]:
					self.xferMat[i,:]=0
					self.xferMat[:,i]=0
				self.xferMat[i,i]=1.
		else:
			self.xferMat=np.eye(self.N)
			
	
	def step(self,Amps_in):
		#performs the transfer matrix operation
		self.Amps=Amps_in
		self.outs=np.dot(self.xferMat,Amps_in)
		return self.outs
		
	def reverse(self):
		#reverses the tranfer matrix operation. This is called particularly
		#after the transfer matrix has changed in order to prevent discontinuities
		#in the input code (typically feedbackLockIn)
		self.Amps=np.dot(np.linalg.inv(self.xferMat),self.outs)
		return self.Amps
		
		
	
		