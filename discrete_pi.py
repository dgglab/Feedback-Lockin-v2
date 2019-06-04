'''
A DiscretePI object acts a PI feedback
loop. It is discrete in the sense that it takes in an input and produces
an output everytime "step" is called; there is no explicit timebase. It can
operate on an arbitrary number of channels in parallel and can disable specific
outputs. It also can be set to take one of its inputs as an offset reference.
'''
import numpy as np


class DiscretePI(object):
    def __init__(self):
        self.Ki=[0]
        self.Kp=[0]
        self.IErr=[]
        self.SetPoints=[]
        self.inputs=[]
        self.N=0
        self.maxes=[np.inf]
        self.mins=[-np.inf]
        self.firstCall = True
        self.inputReferenceIdx = -1
        self.outputsDisabled=False
        self.disabledOutputs=np.zeros(1, dtype=bool)

    def setKint(self,Ki_in):
        # sets the integral feedback constant
        Ki_in = self.checkLengthandUpdate(Ki_in)
        for i in range(self.N):
            if Ki_in[i] == 0:
                self.IErr[i]=0
        self.Ki=Ki_in

    def setKprop(self,Kp_in):
        # sets the proportional feedback constant
        Kp_in = self.checkLengthandUpdate(Kp_in)
        self.Kp=Kp_in

    def setReferenceIdx(self,Idx):
        #sets the index of the channel being used as a reference
        #if <0 the reference value is zero
        self.inputReferenceIdx = Idx

    def setNparams(self,N_in):
        # sets the number of parallel feedback channels
        if not self.N==N_in:
            self.N=N_in
            self.IErr=np.zeros(N_in)
            self.SetPoints=np.zeros(N_in)
            self.inputs=np.zeros(N_in)
            self.Ki=np.ones(N_in)*self.Ki[0]
            self.Kp=np.ones(N_in)*self.Kp[0]
            self.mins=np.ones(N_in)*self.mins[0]
            self.maxes=np.ones(N_in)*self.maxes[0]
            self.disabledOutputs=np.zeros(N_in,dtype=bool)

    def updateSetPoints(self,SetPoints_in):
        # updates the stored set points
        SetPoints_in = self.checkLengthandUpdate(SetPoints_in)
        # seemless change of IErr
        for i in range(self.N):
            if not self.Ki[i] == 0:
                self.IErr[i]+=(self.SetPoints[i]-SetPoints_in[i])*self.Kp[i]/self.Ki[i]
        self.SetPoints=SetPoints_in

    def updateSingleSetpoint(self,SetPoint_in,idx):
        # updates a single setpoint at index=idx.
        if not self.Ki[idx] == 0:
            self.IErr[idx]+=(self.SetPoints[idx]-SetPoint_in)*self.Kp[idx]/self.Ki[idx]
        self.SetPoints[idx]=SetPoint_in

    def setLimits(self,mins,maxes):
        #set the bounds for output values
        if self.varLength(mins)==1:
            # set all to same if single element entered
            self.mins=mins*np.ones(self.N)
            self.maxes=maxes*np.ones(self.N)
        else:
            self.mins=mins
            self.maxes=maxes

    def step(self,inputs):
        # Performs one step of the PI loop
        # store inputs
        #subtract of one signal as a reference
        if self.inputReferenceIdx<0:
            self.inputs=inputs
        else:
            self.inputs= inputs-inputs[self.inputReferenceIdx]

        if self.firstCall:
            # initialize error value
            self.IErr = 0
            self. firstCall = False

        # check that there are the right number of elements in inputs
        if not self.varLength(inputs)==self.N:
            print("Wrong Number of elements")
            return 0

        # calculate errors
        Err=(self.SetPoints-self.inputs)
        self.IErr+=Err*self.Ki

        # maintains zeroed out error if channels are disabled
        if self.outputsDisabled:
            for i in range(self.N):
                if self.disabledOutputs[i]:
                    self.IErr[i]=0

        # raw output signal
        out=Err*self.Kp+self.IErr

        # outputs nan for disabled axes
        if self.outputsDisabled:
            for i in range(self.N):
                if self.disabledOutputs[i]:
                    out[i]=np.nan

        # constrain by the bounds and don't let IErr run away
        for i in range(self.N):
            if out[i]<self.mins[i]:
                out[i]=self.mins[i]
                self.IErr-=Err*self.Ki
            if out[i]>self.maxes[i]:
                out[i]=self.maxes[i]
                self.IErr-=Err*self.Ki

        # returns output signal
        return out

    def zeroErrors(self,input=None):
        # resets IErr to assume the proportional error is zero
        # This is valuable if you discontinuously change the physical
        # system and want let it smoothly find a new equilibrium
        if not input is None:
            self.IErr=input
        else:
            self.IErr=self.step(self.inputs)

    def set_output_enabled(self, idx, enabled):
        self.disabledOutputs[idx] = not enabled
        self.outputsDisabled = np.sum(self.disabledOutputs) == 0

    def varLength(self,input):
        # returns the length of an input, with 1 for a scalar
        # and the length of a vector
        if isinstance(input,(int,float,np.number)):
            return 1
        else:
            return np.shape(input)[0]

    def checkLengthandUpdate(self,input):
        # checks the length of an input and determines if it is
        # a scalar or vector. If the vector length is different than
        # the internal length, it updates.
        N_in=self.varLength(input)
        if self.N==0:
            #initialization condition
            self.setNparams(N_in)
            if N_in == 1:
                output = [input]
            else:
                output = input
        elif N_in==1:
            # produces an array of the input value if scalar
            output=np.ones(self.N)*input
        elif not N_in == self.N:
            # changes number of internal parameters if necessary
            self.setNparams(N_in)
            output = input
        # outputs the input value after necesary modifications
        return output
