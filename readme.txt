This is a brief sketch of the feedbackLockin Control code. The overarching purpose of this
system is to provide the ability to measure AC voltages and apply AC currents to several leads
of a given device. It has the capability to control the current passing through a given lead
to reach a desired set-point inorder to mimic a low-impedance source. Without feedback, it can
serve as a multi-terminal lock-in.  

feedbackLockinControl

feedbackLockinControl.py generates a GUI for interacting with a feedbackLockin object.
It functions to give users control over the setpoint for the output voltages in the
feedbackLockin and ties the feedbackLockin to a physical device. The code connects
the function of a daqDevice (the actual hardware) with the feedbackLockin code that
computes the control signals used. It also can be configured with the variable
"tcpipEngineOut" to make a TCPIP connection to other software for real-time data transfer.

	feedbackLockin

	feedbackLockin.py defines a feedbackLockin object, which functions as multi-terminal
	lock-in amplifier with feedback to maintain certain setpoints. Its intended function
	is to allow for sourcing of current to contacts of a multi-terminal device in order
	to conrol the potential at certain nodes. In particular, it can act to set virtual 
	grounds in the device and record the current passing into our out of each node.

		sinOutputs
		
		sinOutputs.py makes a sinOutputs object that can emit an array of
		sine curves with individual amplitudes (Amps) with a given number
		of points in each sine (Npoints).

		
		lockInCalculator

		lockInCalculator.py creates a lockInCalculator object. This computes the X and Y component
		of a timeseries of length Npoints at a frequency of f = 1/Npoints

		discretePI

		discretePI.py creates a discretePI object which acts a PI feedback
		loop. It is discrete in the sense that it takes in an input and produces
		an output everytime "step" is called; there is no explicit timebase. It can
		operate on an arbitrary number of channels in parallel and can disable specific
		outputs. It also can be set to take one of its inputs as an offset reference.

		biasResistor
		
		biasResistor.py creates a biasResistor object. The main function of the object
		is to map "Amps_in" to "outs" in a manner that approximately conserves current
		assuming similar valued bias resistors for each input. This is tied into the 
		smooth operation of "feedbackLockIn" objects so that feedback signals do not 
		drastically alter the DC potential of a device. 
	
	
	
	movingAverager

	movingAverager.py creates a movingAverager object. This performs a simple
	exponential moving average. The main input Nave_in is the exponential decay
	constant in units of function calls. Everytime "step" is called, it updates
	its stored value and returns the result. It can act on vectors or scalars.


	daqLockInHardware

	daqLockInHardware.py defines daqLockInHardware objects which serve as the low-level
	interface to the ni DAQ cards used for continuous reading and writing. It has written-in
	connections of external clock signals that are to be hardwired between output and input
	DAQ cards. The basic function is that it starts two parallel threads that handle output
	and inputs separately. The output DAQ is set-up to only write when its buffer is empty
	so that there cannot be a build-up of more than a single cycle delay. The input DAQ takes
	its clock signal from the output DAQ and is started first, so that they are synchronized.
	Before running this, NI drivers as well as pyDAQmx need to be installed.

	dummyDevice

	dummyDevice.py defines a dummyDevice object. This is meant to mimic the behavior
	of a NIboard and a physical resistor network between the outputs and inputs. it 
	uses a transferMatrixModel to generate a random resistor network and adds noise to
	the output signal to simulate a real device measurement

		transferMatrixModel
		
		transferMatrixModel.py creates a transferMatrixModel object. It is a general
		transfer matrix object that can store an arbirary NxN matrix and perform 
		matrix multiplication on an N element vector. It particularly has built-in
		functions for creating model conductance/resistance matrices to simulate the
		outputs of a given multi-terminal device


	tcpipXferServer

	tcpipXferServer.py defines a tcpipXferServer object that creates a TCP/IP server socket
	on the localhost and can send data via the socket to other programs (such as MATLAB).


	