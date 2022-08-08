
# %load C:\Users\dgglab\Desktop\Feedback-Lockin-v2\scripts\feedbackLockin_qcodes_module.py
import time
import numpy as np
import socket
import array
import csv
from functools import partial

import qcodes as qc
from qcodes import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.instrument.channel import MultiChannelInstrumentParameter
from qcodes.utils import validators as vals

class FeedbackLockin(Instrument):
    """
    Draft driver for the Feedback Lockin custom instrument (version 2)
    Evgeny Mikheev, 19/05/26;
    Han Hiller updated 8/7/22 

	# usage example:
	# FBL = FeedbackLockin('FBL', TCPport=10000)
	# FBL.connectTCP()
	# FBL.TCPdata.get(); # to fetch data from the TCP connection
	# data=FBL.data; # to access stored data without calling the TCP connection
    """
    
    
    def __init__(self, name, TCPport, **kwargs):
        super().__init__(name, **kwargs)
        self.TCPport=TCPport
        self.nChannels=32 # N of FBL channels
        self.nVars=4 # N of variables sent through TCP
        self.nGainSettings=4 #number of gain settings
        self.nCurrentSettings = 3 #no data for the shorted connection was stored, so the 3 resistors correspond to the output settings
        self.socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM) # set up socket
        self.standardWaitTime = 0.01
        
        # gain and output current calibrations stored in CSV file
        self.gains = np.zeros([self.nChannels,self.nGainSettings])
        self.Iout_ref = np.zeros([self.nChannels, self.nCurrentSettings])
        
        path = 'C:/Users/barna/Documents/Feedback-Lockin-v2-master/scripts'
        with open(f'{path}/fbl_channelGains.csv', newline='\n') as gainCalibration:
            reader = csv.reader(gainCalibration)
            for ch,row in enumerate(reader):
                self.gains[ch,:]= row
                
        with open(f'{path}/fbl_currents.csv', newline='\n') as currentCalibration:
            reader = csv.reader(currentCalibration)
            for ch,row in enumerate(reader):
                self.Iout_ref[ch,:] = row

        self.add_parameter('ki', set_cmd=self.set_ki)
        self.add_parameter('TCPdata',get_cmd=self.save_TCP_data, unit='V') # save all variables from all channels                 
        self.add_parameter('allData',get_cmd=self.get_stored_data, unit='V') # get all variables from all channels             
        self.add_parameter('autoTune', set_cmd=partial(self.autoTune))# auto-adjust the Ki control parameter
        
        # these parameters store the data for specific channels
        for ch in range(self.nChannels):
            self.add_parameter(f'ch{ch}_data',
                           get_cmd=partial(self.ch_getData, ch=ch), unit='V')
        
        # store the input voltage (to the amplifiers prior to amplification) calculated from the amplified signal
        # getVin/calibratedGain for all given channels and gain settings
        # gain settings labeled 0-3
        for gainSetting in range(self.nGainSettings):
            for ch in range(self.nChannels):   
                self.add_parameter(f'ch{ch}_Vin{gainSetting}', get_cmd=partial(self.getVin, ch=ch, gain=self.gains[ch,gainSetting]), unit='V')
         
        # store the output voltages emiited from the computer
        # this is settable
        for ch in range(self.nChannels):
            self.add_parameter(f'ch{ch}_Vout', get_cmd=partial(self.getVout, ch=ch), set_cmd=partial(self.setVout, ch), unit='V')       
                
        # store the output current calclated from the amplitude of the signal sourced from the computer
        # getVout * currentCalibration
        # this is settable
        # current settings labled 1-3 (1 corresponds to the switch in the 2nd pos.)
        for setting in range(self.nCurrentSettings):
            setting+=1
            for ch in range(self.nChannels):
                self.add_parameter(f'ch{ch}_Iout{setting}', get_cmd=partial(self.getIout, ch=ch, Iref = self.Iout_ref[ch, setting-1]), set_cmd=partial(self.setIout, ch, self.Iout_ref[ch, setting-1]), unit='A') 
              
        # feedback on/off and setpoint parameters
        #self.feedbackState = np.zeros(self.nChannels)        
        for ch in range(self.nChannels):
            self.add_parameter(f'ch{ch}_feedback', set_cmd=partial(self.setFeedback, ch))
            self.add_parameter(f'ch{ch}_setPoint', set_cmd=partial(self.setSP, ch), get_cmd=partial(self.getSP, ch=ch), unit='V' )
        self.add_parameter('fbState', get_cmd=self.get_fbState) # get feedback state, 0 for off, 1 for on   
          
        self.data=np.zeros([32,4])
        
        # set up reference channel
        self._refCh = 0
        self.add_parameter('refCh', set_cmd=self.set_refCh)
            
    def connectTCP(self):        
        server_address = ('localhost',self.TCPport)
        self.socket.connect(server_address)
        time.sleep(self.standardWaitTime)
        
        # get feedback state
        self._fbState = self.get_fbState()
        time.sleep(self.standardWaitTime)
        print('connected to FBL TCP server')

    def closeTCP(self):        
        self.socket.close()
        self.socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('disconnected from FBL TCP server')


    def get_TCP_data(self):
        # gets FBL data via TCP connection
        
        self.socket.sendall(b'sendData\n')
        time.sleep(self.standardWaitTime)

        TCPdata = self.socket.recv(self.nVars*8*self.nChannels);
        data=np.array(array.array('d',TCPdata))
        data=data.reshape(self.nChannels,self.nVars, order='F')
        self.data=data
        time.sleep(self.standardWaitTime)
         

    def save_TCP_data(self):
        # wait for stable voltages on the feedback enabled inputs, if any
        
        time.sleep(self.standardWaitTime)
        
        if 1 in self._fbState:
            self.data = self.waitFor_stable_fbData()
        else:
            self.get_TCP_data()
 
     
    def get_stored_data(self):
        data=self.data
        return data
        
    def autoTune(self, factor):
        self.socket.sendall(f'autoTune {factor}\n'.encode('utf-8'))
        time.sleep(self.standardWaitTime)
    
    def set_ki(self, ki):
        self.socket.sendall(f'setKi {ki}\n'.encode('utf-8'))
        time.sleep(self.standardWaitTime)
    
    def ch_getData(self, ch):
        # recieve data from one of FBL's channels
        # this function is, for the time being, depreciated
        
        self.socket.sendall(f'sendChannel {ch}\n'.encode('utf-8'))
        time.sleep(self.standardWaitTime)
        TCPdata_channel = self.socket.recv(self.nVars*8)
        time.sleep(.1)
        data=np.array(array.array('d',TCPdata_channel))
        time.sleep(self.standardWaitTime)
        return data
        
    def get_fbState(self):
        self.socket.sendall(b'send_fbState\n')
        time.sleep(self.standardWaitTime)
        fbState = self.socket.recv(self.nChannels*8);
        fbState=np.array(array.array('d',fbState))
        fbState=fbState.reshape(self.nChannels, order='F')
        time.sleep(self.standardWaitTime)
                
        return fbState
        
    def get_stored_fbState(self):
        return self._fbState
        
    def waitFor_stable_fbData(self):
        # while the absolute difference of input voltage and setpoints, 
        # averaged over all feedback enabled channels, is larger than a threshold, keep sampling 
        threshold = 0.05
        self.get_TCP_data()
       
        t0= time.time()
        while self.compute_SPdif() > threshold:
        
            # set a maximum wait time of 10s
            if time.time()-t0>5:
                break
                
            self.get_TCP_data()
            time.sleep(self.standardWaitTime * 3)
        return self.data
        
    def compute_SPdif(self):
        # returns average absolute difference between setpoints and amplified input voltages
        
        SPs = self.data[:,1][self._fbState==1] + self.data[self._refCh,2] # SP + refCh voltage
        inputVs = self.data[:,2][self._fbState==1]
        n_fbEnabled = len(self._fbState[self._fbState==1])
        
        avg_dif = np.sum([abs(dif) for dif in (SPs - inputVs)])/n_fbEnabled
        return avg_dif
    
    def getVin_chData(self, ch, gain):
        inputV = self.ch_getData(ch)[2]/gain
        return inputV
    
    def getSP(self, ch):
        SP = self.data[ch, 1]
        return SP
        
    def setSP(self, ch, setPoint):
        self.socket.sendall(bytes(f'setV {ch} {setPoint}\n', encoding='UTF-8'))
        time.sleep(self.standardWaitTime)
   
    def getVin(self, ch, gain):
        inputV = self.data[ch, 2]/gain
        return inputV
    
    def getVout(self, ch):
        outputV = self.data[ch,0]
        return outputV
    
    def getIout(self, ch, Iref):
        outputV = self.getVout(ch)
        outputI = outputV * Iref
        return outputI
        
    def setVout(self, ch, Vout):
        Vout = round(Vout, 3)
        self.socket.sendall(bytes(f'setI {ch} {Vout}\n', encoding='UTF-8'))
        time.sleep(self.standardWaitTime)
                             
    def setIout(self, ch, Iref, Iout):
        Vout = round(Iout/Iref, 3)
        self.setVout( ch, Vout)
       
    def setCorrectionFactor(self,correctionFactor):
        self.socket.sendall(bytes(f'setCf {correctionFactor}\n', encoding='UTF-8'))
        time.sleep(self.standardWaitTime)
        
    def setFeedback(self, ch, onOff):
        
        self.socket.sendall(bytes(f'setFeed {ch} {onOff}\n', encoding='UTF-8'))
        time.sleep(self.standardWaitTime)
        self._fbState = self.get_fbState()

    def reset_averaging(self):
        self.socket.sendall(b'reset_avg\n')
        time.sleep(self.standardWaitTime)
        
    def set_refCh(self, ch):
        # currently this is only used to register the reference channel with the qcodes driver, 
        # it does not actually update the reference channel in the feedback lockin instrument
        
        self._refCh = ch
   

class parseVin(Instrument):
    # Meta-instrument for reading an input channel
    # from stored data without calling the TCP connection
    # usage example:
    # in1=parseVin('in1',fbl=FBL,chO=1,ampO=1e4)

    def __init__(self,name,fbl,chO,ampO,**kwargs):
            super().__init__(name, **kwargs)
            self.fbl=fbl
            self.chO=chO
            self.ampO=ampO
            self.add_parameter('Vin',get_cmd=self._getVin,unit='V')
            self.add_parameter('Phase',get_cmd=self._getPhase,unit='deg')
    def _getVin(self):
        data=self.fbl.stored_data.get();

        return data[self.chO,2]/self.ampO
    def _getPhase(self):
        data=self.fbl.stored_data.get();
        return data[self.chO,3]        

class parseVout(Instrument):
    # Meta-instrument for reading an output channel
    # from stored data without calling the TCP connection
    # usage example:
    # out1=parseVout('out1',fbl=FBL,chO=1,ampO=1e4)
    def __init__(self,name,fbl,chO,ampO,**kwargs):
            super().__init__(name, **kwargs)
            self.fbl=fbl
            self.chO=chO
            self.ampO=ampO
            self.add_parameter('Vout',get_cmd=self._getVout,unit='V')
    def _getVout(self):
        data=self.fbl.stored_data.get();
        return data[self.chO,0]/self.ampO

        
class parseR_chA_chB_chI(Instrument):
    # Meta-instrument for reading 3 input channels into a resistance
    # from stored data without calling the TCP connection
    # usage example:
    # Rxx=getR_chA_chB_chI('Rxx',fbl=FBL,chA=0,ampA=1e4,chB=1,ampB=1e5,chI=2,ampI=1e5,R2GND=470)
    def __init__(self,name,fbl,chA,ampA,chB,ampB,chI,ampI,R2GND,**kwargs):
        super().__init__(name, **kwargs)
        self.fbl=fbl
        self.chA=chA
        self.ampA=ampA
        self.chB=chB
        self.ampB=ampB
        self.chI=chI       
        self.ampI= ampI       
        self.R2GND=R2GND
        self.add_parameter('R',get_cmd=self._getR,unit='Ohms') 
        self.add_parameter('I',get_cmd=self._getI,unit='A') 
        self.add_parameter('VA',get_cmd=self._getVA,unit='V')
        self.add_parameter('VB',get_cmd=self._getVB,unit='V')
        self.add_parameter('PhaseA',get_cmd=self._getPhaseA,unit='deg')
        self.add_parameter('PhaseB',get_cmd=self._getPhaseB,unit='deg')
        self.add_parameter('PhaseI',get_cmd=self._getPhaseI,unit='deg')
        
    def _getR(self):
        data=self.fbl.stored_data.get();
        return (data[self.chA,2]/self.ampA-data[self.chB,2]/self.ampB)/(data[self.chI,2]/self.ampI/self.R2GND)
    def _getI(self):
        data=self.fbl.stored_data.get();
        return data[self.chI,2]/self.ampI/self.R2GND
    def _getVA(self):
        data=self.fbl.stored_data.get();
        return data[self.chA,2]/self.ampA
    def _getVB(self):
        data=self.fbl.stored_data.get();
        return data[self.chB,2]/self.ampB
    def _getPhaseA(self):
        data=self.fbl.stored_data.get();
        return data[self.chA,3]
    def _getPhaseB(self):
        data=self.fbl.stored_data.get();
        return data[self.chB,3]
    def _getPhaseI(self):
        data=self.fbl.stored_data.get();
        return data[self.chI,3]

class parseR_chA_chI(Instrument):
    # Meta-instrument for reading 2 input channels (A-B and Isrc) into a resistance
    # from stored data without calling the TCP connection
    # usage example:
    # Rxx=getR_chA_chI('Rxx',fbl=FBL,chA=0,ampA=1e4,chI=2,ampI=1e5,R2GND=470)
    def __init__(self,name,fbl,chA,ampA,chI,ampI,R2GND,**kwargs):
        super().__init__(name, **kwargs)
        self.fbl=fbl
        self.chA=chA
        self.ampA=ampA
        self.chI=chI       
        self.ampI= ampI       
        self.R2GND=R2GND
        self.add_parameter('R',get_cmd=self._getR,unit='Ohms') 
        self.add_parameter('I',get_cmd=self._getI,unit='A') 
        self.add_parameter('VA',get_cmd=self._getVA,unit='V')
        self.add_parameter('PhaseA',get_cmd=self._getPhaseA,unit='deg')
        self.add_parameter('PhaseI',get_cmd=self._getPhaseI,unit='deg')
        
    def _getR(self):
        data=self.fbl.stored_data.get();
        return data[self.chA,2]/self.ampA/(data[self.chI,2]/self.ampI/self.R2GND)
    def _getI(self):
        data=self.fbl.stored_data.get();
        return data[self.chI,2]/self.ampI/self.R2GND
    def _getVA(self):
        data=self.fbl.stored_data.get();
        return data[self.chA,2]/self.ampA
    def _getPhaseA(self):
        data=self.fbl.stored_data.get();
        return data[self.chA,3]
    def _getPhaseI(self):
        data=self.fbl.stored_data.get();
        return data[self.chI,3]    
    
class parseT_OCT(Instrument):
    # Meta-instrument for converting resistance from another meta-instrument into temperature, using a calibration file 
    # usage example:
    # Roct=parseR_chA_chB_chI('Roct',fbl=FBL,chA=0,ampA=1e4,chB=1,ampB=1e5,chI=2,ampI=1e5,R2GND=470)
    # calfilename = "D:/Dropbox (DGG Lab)/Cryocooler/Main/Evgeny/Lakeshore/R16C19.dat"
    # OCT=parseT_OCT('OCT',R=Roct,calfilename=calfilename)
    def __init__(self,name,R,calfilename,**kwargs):
        super().__init__(name, **kwargs)
        self.R=R
        self.cal=np.loadtxt(calfilename,skiprows=2)
        self.add_parameter('Toct',get_cmd=self._get_Toct,unit='K')
        self.add_parameter('Roct',get_cmd=self._get_Roct,unit='Ohms')

    def _get_Roct(self):
        Roct = self.R.R.get()
        return Roct
    def _get_Toct(self):
        Roct = self.R.R.get()
        return np.interp(Roct,np.flipud(self.cal[:,1]),np.flipud(self.cal[:,0]));