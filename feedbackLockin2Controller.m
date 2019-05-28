%{
feedbackLockinController objects are a matlab interface for reading out
data from the feedbackLockin python program via TCP/IP socket connection.
At present, it is configured to read 24 double precision numbers for three
parameters from 8 channels. 
%}
classdef feedbackLockin2Controller < handle
    
    properties
       
        tcpConnection
        dataStore = zeros(32,1);
        Vout
        Vin
        Vmeas
        Phase
    end
    

    methods
       
        function openConnection(obj,PortNum)
            %opens a tcpip connection with 
            obj.tcpConnection = tcpip('localhost', PortNum, 'NetworkRole', 'client');
            obj.tcpConnection.ByteOrder= 'littleEndian';
            fopen(obj.tcpConnection);
            
        end
        
        function readData(obj)
            %reads data from the TCP/IP connection when data is available
            %and clears the buffer 
            bytesAvailable = obj.tcpConnection.BytesAvailable;
            
            if bytesAvailable >= 32*8
                obj.dataStore = fread(obj.tcpConnection,32,'double');
            end
            if obj.tcpConnection.BytesAvailable > 0
                fread(obj.tcpConnection,obj.tcpConnection.BytesAvailable/8,'double'); %purges the buffer
            end
        end
        
        function sendDataCommand(obj)
            % sends the "sendData" command to the python software
            fwrite(obj.tcpConnection,['sendData',char(10)]);
                
        end
        

        
        function getData(obj)
            % retreives data by sequentially requesting data and reading it
            % out. it populates the internal variables associated with the
            % channels sent by the feedbackLockin program
            obj.sendDataCommand();
            
            while obj.tcpConnection.BytesAvailable < 32*8
                pause(.01);
            end
            
            obj.readData();
            
            obj.Vout=obj.dataStore(1:8);
            obj.Vin =obj.dataStore(9:16);
            obj.Vmeas=obj.dataStore(17:24);
            obj.Phase=obj.dataStore(25:32);
            
        end
        function closeConnection(obj)
            % closes the connection. 
            fclose(obj.tcpConnection);
            
        end
        
         function setV(obj,idx,val)
            fwrite(obj.tcpConnection,['setV ',num2str(idx),' ',num2str(val),char(10)]);
        end
        
        function setI(obj,idx,val)
            fwrite(obj.tcpConnection,['setI ',num2str(idx),' ',num2str(val),char(10)]);
        end
        
        function setKi(obj,val)
            fwrite(obj.tcpConnection,['setKi ',num2str(val),char(10)]);
        end
        
        function setFeed(obj,idx,val)
            fwrite(obj.tcpConnection,['setFeed ',num2str(idx),' ',num2str(val),char(10)]);
        end
        
        function autoTune(obj,varargin)
            if nargin==1
                fwrite(obj.tcpConnection,['autoTune',char(10)]);
            else
                   fwrite(obj.tcpConnection,['autoTune ',num2str(varargin{1}),char(10)]);
            end
        end
        
    end
        
end