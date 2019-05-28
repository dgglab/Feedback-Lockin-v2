from pyqtgraph.Qt import QtGui, QtCore, USE_PYSIDE, USE_PYQT5
import numpy as np

import mainwindow
import time
import configparser as cp
from feedbackLockin import feedbackLockin
from tcpipXferServer import tcpipXferServer
from movingAverager import movingAverager
'''
feedbackLockinControl.py generates a GUI for interacting with a feedbackLockin object.
It functions to give users control over the setpoint for the output voltages in the
feedbackLockin and ties the feedbackLockin to a physical device. The code connects
the function of a daqDevice (the actual hardware) with the feedbackLockin code that
computes the control signals used. It also can be configured with the variable
"tcpipEngineOut" to make a TCPIP connection to other software for real-time data transfer.
'''

config = cp.ConfigParser(interpolation=cp.ExtendedInterpolation())
config.read('feedbackLockin.ini')

samplesPerSine = int(config['DEFAULT']['samplesPerSine'])
lockinFrequency = float(config['DEFAULT']['lockinFrequency'])
nAveForOutput = eval(config['TCP output']['nAveForOUTPUT'])

runOffline = config['DEFAULT'].getboolean('run offline')

try: tcpipEngineOut = config['TCP output'].getboolean('tcp Output enabled')
except: tcpipEngineOut = False

try: tcpPortNumber = int(config['TCP output']['local host port'])
except: tcpPortNumber = 10000

try: nChannels = int(config['DEFAULT']['Number of Channels'])
except: nChannels = 8

try: refChannel=int(config['feedbackLockin']['voltage reference channel'])
except:	refChannel = 0

try: initFeedback = [bool(int(s)) for s in config['DEFAULT']['feedback enabled'].split(",")]
except: initFeedback = (False,False,False,False,False,False,False,False)

try: initSetPoints = [float(s) for s in config['DEFAULT']['initial setpoints'].split(",")]
except: initSetPoints = [0,0,0,0,0,0,0,0]


try: initKint = float(config['feedbackLockin']['initial Kint'])
except: initKint = 0.010	

try: initKprop = float(config['feedbackLockin']['initial Kprop'])
except: initKprop = 0.0

try: initAve = float(config['feedbackLockin']['number of cycles for averaging'])
except: initAve = 1

try: inputChannels = config['DAQ']['input channels']
except: inputChannels = "ai8_2,ai8,ai9,ai10,ai11,ai12,ai13,ai14,ai15"

try: outputChannels = config['DAQ']['output channels']
except: outputChannels = "Dev1/ao0:7"

try: outputClock = config['DAQ']['output clock']
except: outputClock = "/Dev3/ao/SampleClock"

try: outputClockChannel = config['DAQ']['output clock channel']
except: outputClockChannel = "/Dev3/PFI7"

try: inputClockChannel = config['DAQ']['input clock channel']
except: inputClockChannel = "/Dev1/PFI7"


# feedBackLockin is the main object that handles the control and feedback of the 
# overall lock-in system
feedBackLockin=feedbackLockin()
feedBackLockin.setNpoints(samplesPerSine)
print(nChannels)
feedBackLockin.setNparam(nChannels)
feedBackLockin.updateFeedback(initKint,initKprop)

if runOffline:
	#uses a dummy model of  the daq card to test the code
	from dummyDevice import dummyDevice
	daqDevice = dummyDevice()
	daqDevice.setNparam(nChannels)
	daqDevice.setRingOutput()
else:
	#daqDevice is the DAQ hardware interface object 
	from daqLockInHardware import daqLockInHardware
	daqDevice=daqLockInHardware()
	daqDevice.setNparam(nChannels)
	daqDevice.setNpoints(samplesPerSine)
	daqDevice.frequency = lockinFrequency
	daqDevice.setSampleRate()
	daqDevice.inputChannels(inputChannels)  
	# we use global virtual channels that point to real physical channels	
	# for the input. This is done so that we can repeat the first channel
	# to eliminate an artifact of the DAQ's multiplexing
	daqDevice.outputChannels(outputChannels)
	daqDevice.setClocks(outputClock,outputClockChannel,inputClockChannel)


#initialize the GUI
app = QtGui.QApplication([])
win = QtGui.QMainWindow()
ui = mainwindow.Ui_mainWindow()
ui.setupUi(win)
win.setWindowTitle('Feedback Lockin')

win.show()

if tcpipEngineOut:
	#tcpXfer is an object that handles tcpip connections for data transfer
	tcpXfer = tcpipXferServer()
	tcpXfer.setPortNum(tcpPortNumber)
	tcpXfer.startListening()	
	tcpXfer.acceptConnections()
	outAverage = movingAverager()
	outAverage.setAveraging(nAveForOutput)


global outAveIndex #outAveIndex counts the number of cycles since last Export
outAveIndex = 0
def exportOnSocket():
	global outAveIndex
	# function that sends data to other software when the "sendData" command
	# is received on TCPIP connection.
	if tcpipEngineOut:
		temp=np.append(feedBackLockin.vOuts,feedBackLockin.vIns)
		temp=np.append(temp,feedBackLockin.ACins)
		temp=np.append(temp,feedBackLockin.Phaseins)

		if outAveIndex>5:
			temp=outAverage.step(temp)
		outAveIndex+=1
		commands=tcpXfer.readFromPort()
		parseCommands(commands)

def parseCommands(commandsIn):
	# function that parses TCPIP commands from host program
	if commandsIn is not None:
		for command in commandsIn:
			try:
				if command == 'sendData':
					tcpXfer.sendDataOut(outAverage.oldData)
					outAveIndex=0
					
				elif 'setV' in command:
					_,idx,amp=command.split(' ')
					voltsIn[int(idx)].setValue(float(amp))
				elif 'setI' in command:
					_,idx,amp=command.split(' ')
					voltsOut[int(idx)].setValue(float(amp))
				elif 'setKi' in command:
					_,amp=command.split(' ')
					ui.Kint.setValue(float(amp))
				elif 'setFeed' in command:
					_,idx,amp=command.split(' ')
					print(int(idx),bool(int(amp)))
					feedBack[int(idx)].setChecked(bool(int(amp)))
				elif 'autoTune' in command:
					temp=command.split(' ')
					if len(temp)==1:
						ui.Kint.setValue(feedBackLockin.autoTunePID())
					else:
						ui.Kint.setValue(feedBackLockin.autoTunePID(float(temp[1])))
					
			except:
				print("Error in feedbackLockinGUI.parseCommands")
			
 
def updateAmps(input):
	#slot for updating outputs when feedback is off
	idxIn=int(ui.centralwidget.sender().objectName().replace("voltOut",""))-0
	feedBackLockin.updateAmps(input,idxIn)
	
def updateAve(input):
	#slot for changing internal averaging of signal
	feedBackLockin.updateAve(input)
	
def updateSetPoints(input):
	#slot for updating feedback setpoints
	idxIn=int(ui.centralwidget.sender().objectName().replace("voltIn",""))-0
	feedBackLockin.updateSetpoints(input,idxIn)

def updateFeedback():
	#slot for changing feedback constants
	feedBackLockin.updateFeedback(ui.Kint.value(),ui.Kprop.value())

def setSignalReference(input):
	#sets the index of the channel being used as a reference
	#if <0 the reference value is zero
	feedBackLockin.setReference(input-0)
	if input>0:
		feedBack[input-0].setChecked(False)
		
def updateOffset(input):
	#slot for changing DC offset
	#print(input)
	feedBackLockin.offset = input
	feedBack[input].setChecked(False)
	
def toggleFeedback(input):
	#slot for enabling/disabling feedback
	idxIn=int(ui.centralwidget.sender().objectName().replace("feedBack",""))-0
	if input:
		#feedback is on
		voltsOut[idxIn].valueChanged.disconnect(updateAmps)
		voltsIn[idxIn].setEnabled(True)

		feedBackLockin.enableFeedback(idxIn)
	else:
		#feedback is off
		voltsOut[idxIn].valueChanged.connect(updateAmps)
		voltsIn[idxIn].setEnabled(False)

		feedBackLockin.disableFeedback(idxIn)
		
#arrays for different QDoubleSliders
voltsOut=[]
voltsIn =[]
feedBack=[]
ACins = []
Phaseins = []

for i in range(nChannels):
	eval("voltsOut.append(ui.voltOut%d)" % (i+0))
	eval("voltsIn.append(ui.voltIn%d)" % (i+0))
	eval("feedBack.append(ui.feedBack%d)" % (i+0))
	eval("ACins.append(ui.ACin%d)" % (i+0))
	eval("Phaseins.append(ui.Phasein%d)" % (i+0))
	voltsIn[i].valueChanged.connect(updateSetPoints)
	voltsIn[i].setValue(initSetPoints[i])
	feedBack[i].setChecked(True)
	feedBack[i].stateChanged.connect(toggleFeedback)
	if not initFeedback[i]:
		feedBack[i].setChecked(False)
#initialize and connect control parameters for feedback
ui.averageVal.valueChanged.connect(updateAve)
ui.averageVal.setValue(initAve)
ui.referenceChannel.valueChanged.connect(setSignalReference)
ui.referenceChannel.setValue(refChannel)

ui.Kint.setValue(feedBackLockin.Kint)
ui.Kprop.valueChanged.connect(updateFeedback)
ui.Kint.valueChanged.connect(updateFeedback)


#initializing plotWidget for displaying input data
vInPlot = ui.vInPlotWidget.addPlot()
curves = []
for i in range(feedBackLockin.sines.Nstreams):
	curves.append(vInPlot.plot(pen=i))
	

ptr = 0
def update():
	global curve, data, ptr, vInPlot
	
	#sends output signal to device
	daqDevice.readIn(feedBackLockin.sineOut())
	
	#reads data from device
	data=daqDevice.OutputData()
	
	#send data to lock-in for generating feedback
	feedBackLockin.readIn(data.T)
	
	for i in range(feedBackLockin.Nparam):
		#update data in GUI
		curves[i].setData(data.T[i])
		ACins[i].setValue(feedBackLockin.ACins[i])
		Phaseins[i].setValue(feedBackLockin.Phaseins[i])
		
		if feedBackLockin.feedBackOn[i]:
			#only update if feedback is on	
			voltsOut[i].setValue(feedBackLockin.vOuts[i])
	
	#initialize plot prameters 
	if ptr == 0:
		vInPlot.setYRange(-11,11,padding=0)
		vInPlot.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted
		vInPlot.setMouseEnabled(x=False,y=False)
		vInPlot.setYRange(-11,11,padding=0)
		ptr += 1

	if tcpipEngineOut:
		exportOnSocket()
#when data is acquired in device, take a step
daqDevice.initializeDAQ()
daqDevice.dataAcquired.connect(update)

daqDevice.start()
feedBackLockin.updateFeedback(feedBackLockin.Kint,0)
#first step
update()



if __name__ == '__main__':
	import sys
	if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
		QtGui.QApplication.instance().exec_()
