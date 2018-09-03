import numpy as np
import os
#import matplotlib.pyplot as plt
#import Tkinter as tk
import time, threading
#import tkFileDialog as filedialog
import multiprocessing
import sys

'''
lockInCalculator.py creates a lockInCalculator object. This computes the X and Y component
of a timeseries of length Npoints at a frequency of f = 1/Npoints
'''


class lockInCalculator:
	
	def __init__(self):
	
		self.Npoints=1
		self.sin_ref=np.zeros(1)
		self.cos_ref=np.zeros(1)
		
		self.firstCall = True
		
	def setNpoints(self,N_in):
		
		self.Npoints = N_in
		self.sin_ref = np.sin(2.0*np.pi*np.expand_dims(np.arange(N_in),axis=1)/float(N_in))
		self.cos_ref = np.cos(2.0*np.pi*np.expand_dims(np.arange(N_in),axis=1)/float(N_in))
		self.sin_ref/= np.sum(self.sin_ref ** 2)
		self.cos_ref/= np.sum(self.cos_ref ** 2)

		
	def calcAmps(self,dataIn):
		
		dataDim = np.ndim(dataIn)
		dataShape = np.shape(dataIn)
		if dataDim == 1:
			dataIn=np.expand_dims(dataIn,axis=1)
		if dataShape[0] == self.Npoints:
			return np.sum(self.cos_ref*dataIn,axis=0),np.sum(self.sin_ref*dataIn,axis=0)
	
	def calcAmpsWithDC(self,dataIn):
		dataDim = np.ndim(dataIn)
		if dataDim == 1:
			dataIn=np.expand_dims(dataIn,axis=1)
		return self.calcAmps(dataIn), np.mean(dataIn,axis = 0)
	
	
		
