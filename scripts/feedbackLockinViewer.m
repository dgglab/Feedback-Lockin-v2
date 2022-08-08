%{
feedbackLockinViewer is an object that setsup a non-blocking viewer for the
data stream out of a feedbackLockinControl.py control system via a
feedbackLockinController object.


%}

classdef feedbackLockinViewer < handle
    
    properties
        refreshTimer
        Signal
        Nelements = 8;
        Npoints = 1000;
        lockinObj
        plotObj
    end
    
    methods
        
        function setupTimer(obj)
            obj.refreshTimer=timer('TimerFcn',@(~,~)obj.getDataAndUpdate,...
                'Period',.25,'ExecutionMode','fixedRate');
        end
        
        function init(obj)
            obj.Signal=zeros(obj.Npoints,obj.Nelements);
            obj.createLockinObj();
            obj.setupTimer();
            figure(1);
            plot(0,0);
            obj.plotObj=gca;
        end
        
        function start(obj)
           start(obj.refreshTimer);
        end
        
        function createLockinObj(obj)
            obj.lockinObj = feedbackLockinController();
            obj.lockinObj.openConnection(10000);
        end
        
        function assignLockinObj(obj,lockinObj)
            obj.lockinObj = lockinObj;
        end
        
        function updateData(obj,Vin)

            obj.Signal(1:999,:)=obj.Signal(2:end,:);
            obj.Signal(end,:)=Vin;

            plot(obj.plotObj,obj.Signal);

        end
        
        function getDataAndUpdate(obj)
            obj.lockinObj.getData()
            obj.updateData(obj.lockinObj.Vout)
        end
        
        function stopAndDisconnect(obj)
            stop(obj.refreshTimer);
            delete(obj.refreshTimer);
            delete(obj.lockinObj);
        end
        
    end
end