import numpy as np

'''
movingAverager.py creates a movingAverager object. This performs a simple
exponential moving average. The main input Nave_in is the exponential decay
constant in units of function calls. Everytime "step" is called, it updates
its stored value and returns the result. It can act on vectors or scalars.
'''

class movingAverager:
	
	def __init__(self):
	
		self.setAveraging(1.0)
		self.firstCall = True
	
	def setAveraging(self,Nave_in):
		# sets the decay rate of the stored data
		self.newMult=1.0/Nave_in
		self.oldMult=1-self.newMult
	
	def step(self,dataIn):
		# performs a single step
		if self.firstCall:
			# sets the first value as the input so it doesn't need
			# to rise from 0
			self.firstCall = False
			self.oldData=dataIn
			
		# updates stored value
		self.oldData = self.newMult*dataIn+self.oldMult*self.oldData
		
		# outputs the new average
		return self.oldData
		