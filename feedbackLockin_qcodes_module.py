import time
import numpy as np
import socket
import array
from functools import partial

import qcodes as qc
from qcodes import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.instrument.channel import MultiChannelInstrumentParameter
from qcodes.utils import validators as vals

class FeedbackLockin(Instrument):
    """
    Draft driver for the Feedback Lockin custom instrument (version 2)
    Evgeny Mikheev, 19/05/26
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
        self.socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.add_parameter('TCPdata',
                           get_cmd=self._get_TCP_data,
                           unit='V')
        self.add_parameter('stored_data',
                           get_cmd=self._get_stored_data,
                           unit='V')
        self.data=np.zeros([32,4])
        
        for i in range(self.nChannels):
            self.add_parameter(f'ch{i}_out', unit='V', set_cmd=partial(self._set_v_out, i))  
            self.add_parameter(f'ch{i}_in', unit='V', get_cmd=partial(self._get_single_v, i))  
            
    def connectTCP(self):        
        server_address = ('localhost',self.TCPport)
        self.socket.connect(server_address)

    def _get_TCP_data(self):
        self.socket.sendall(b'sendData\n');
        TCPdata = self.socket.recv(self.nVars*8*self.nChannels);
        data=np.array(array.array('d',TCPdata))
        data=data.reshape(self.nChannels,self.nVars, order='F')
        self.data=data
        return data

    def _get_stored_data(self):
        data=self.data
        return data
    
    def _get_single_v(self, v):
        return self.get_v_in([v])[0][0]
    
    def get_v_in(self, vs):
        d = self.TCPdata.get()
        out = []
        for v in vs:
            out.append((d[:,2][v], d[:,3][v]))
        return out
    
    def _set_v_out(self, c, v):
        self.socket.sendall(bytes(f'setI {c} {v}\n', encoding='UTF-8'))


class getR_chA_chB_chI(Instrument):
	# Meta-instrument for reading 3 input channels into a resistance
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
        self.add_parameter('PhaseI',get_cmd=self._getPhaseB,unit='deg')
        
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




		