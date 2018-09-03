import numpy as np
import socket
import time

'''
tcpipXferServer.py defines a tcpipXferServer object that creates a TCP/IP server socket
on the localhost and can send data via the socket to other programs (such as MATLAB).
'''

class tcpipXferServer():

	def __init__(self):
		
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server_address = ('localhost',10000)
		self.PortNum=10000
	
	def setPortNum(self,PortNum):
		# choose the TCP/IP port number
		self.PortNum=PortNum
		
	def startListening(self):
		# sets up and starts the server socket on the specified Port
		self.server_address = ('localhost',self.PortNum)
		self.sock.bind(self.server_address)
		self.sock.setblocking(0)
		self.sock.listen(1)
		
		
	def acceptConnections(self):
		# checks for available connections and waits until one is established
		try:
			self.connection, self.client_address = self.sock.accept()
			
		except:
			print("waiting for connection...")
			time.sleep(1)
			self.acceptConnections()
			None
		
	def sendDataOut(self,data_out):
		# sends data 
		try:
			self.connection.sendall(data_out.tostring())
		
		except:
			#print("failed to send")
			None
			
	def readDataIn(self):
		#attempts to read from client. 
		try: 
			data = self.connection.recv(4096)
			
		except:
			#print("failed to read")
			data = None
		
		return data
		

	def readFromPort(self):
		
		try:
			readCommands = str(self.connection.recv(4096),'utf-8').split('\n')[:-1]
			#print(readCommands)
		except:
			readCommands = None
			
		return readCommands

	def checkSend(self):
		#checks for the "sendData" command from client
		data= self.readDataIn()
		if not data is None:
			return data[:8] == b'sendData'
		else:
			return False
		
	def checkAndSend(self,data_out):
		# checks for the "sendData" from the client and sends output data
		# if it is received.
		if self.checkSend():
			self.sendDataOut(data_out)
			
	def closeSocket(self):
		# closes the TCP/IP socket
		self.sock.close()
			
		
	def __del__(self):
		self.closeSocket()