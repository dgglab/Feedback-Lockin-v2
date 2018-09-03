import numpy as np
from numpy import random

'''
transferMatrixModel.py creates a transferMatrixModel object. It is a general
transfer matrix object that can store an arbirary NxN matrix and perform 
matrix multiplication on an N element vector. It particularly has built-in
functions for creating model conductance/resistance matrices to simulate the
outputs of a given multi-terminal device
'''



class transferMatrixModel:
	
	def __init__(self):
	
		self.Nchannel=1
		self.xferMatrix=np.ones((1,1))
		
		self.firstCall = True
	
	def setNchannel(self,Nchannel):
		#sets the number of channels to include
		if not self.Nchannel == Nchannel:
			self.Nchannel=Nchannel
			self.makeRing()
			
	def randMatrix(self):
		#produces a viable, random conductance matrix
		self.xferMatrix=random.rand(self.Nchannel,self.Nchannel)/2.0
		self.xferMatrix=-np.dot(self.xferMatrix.T,self.xferMatrix)
		#ensures that DC offsets do not change the output
		self.zeroOutRows()
		
		
	
	def symmetrize(self):
		#symmetrizes the transfer matrix
		self.xferMatrix=(self.xferMatrix+self.xferMatrix.T)/2.0
	
	def antisymmetrize(self):
		#antisymmetrizes the transfer matrix
		self.xferMatrix=(self.xferMatrix-self.xferMatrix.T)/2.0
	
	def zeroOutRows(self):
		#Makes diagonal elements equal to the negative of all other
		#elements in a row. This ensures that the eigenvector (1,1,...,1)
		#has an eigenvalue of zero, meaning that DC offsets in voltage
		#would not produce a change in current
		for i in range(self.Nchannel):
			self.xferMatrix[i,i]-=np.sum(self.xferMatrix[i,:])
			
	def makeRing(self):
		#models a ring of resistors in transfer matrix
		self.xferMatrix=np.zeros((self.Nchannel,self.Nchannel))
		for i in range(self.Nchannel-1):
			self.xferMatrix[i,i+1]=-0.5
			self.xferMatrix[i+1,i]=-0.5
			self.xferMatrix[i,i]=1.0
		self.xferMatrix[-1,-1]=1.0
		self.xferMatrix[0,-1]=-.5
		self.xferMatrix[-1,0]=-.5


	def xfer(self,dataIn):
		#performs matrix multiplcation
		return np.dot(self.xferMatrix,dataIn)
		
	def biasResistorMod(self,R_in):
		#modifies the transfer matrix to presume you have the sitution
		#GV=I=(Vout-V)/R_in so that it transfers from (R_in G+1)V=Vout
		self.xferMatrix=R_in*self.xferMatrix+np.eye(self.Nchannel)
		
	def inv(self):
		#inverts internal transfer matrix.
		self.xferMatrix=np.linalg.inv(self.xferMatrix)
		
	def scale(self,scaleFactor):
		#scales internal transfer matrix
		self.xferMatrix*=scaleFactor

