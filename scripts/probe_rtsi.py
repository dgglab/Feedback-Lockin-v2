"""Verify RTSI7 clock is reaching the 6363 from the 6738."""
from ctypes import byref, c_int32, c_uint32
import time
import numpy as np
import PyDAQmx as mx

ao_task = mx.TaskHandle()
ci_task = mx.TaskHandle()
written = c_int32()
count = c_uint32()

# Start an AO task on the 6738 and export clock to RTSI7
mx.DAQmxCreateTask("", byref(ao_task))
mx.DAQmxCreateAOVoltageChan(ao_task, "ni6738/ao0", "",
        -10.0, 10.0, mx.DAQmx_Val_Volts, None)
mx.DAQmxCfgSampClkTiming(ao_task, "OnboardClock", 100000.0,
        mx.DAQmx_Val_Rising, mx.DAQmx_Val_ContSamps, 100)
mx.DAQmxExportSignal(ao_task, mx.DAQmx_Val_SampleClock, "/ni6738/RTSI7")
data = np.sin(2 * np.pi * np.arange(100) / 100).astype(np.float64)
mx.DAQmxWriteAnalogF64(ao_task, 100, True, 10.0,
        mx.DAQmx_Val_GroupByChannel, data, byref(written), None)
print("AO running, clock on RTSI7")

# Count edges on the 6363's RTSI7 for 2 seconds
mx.DAQmxCreateTask("", byref(ci_task))
mx.DAQmxCreateCICountEdgesChan(ci_task, "ni6363/ctr0", "",
        mx.DAQmx_Val_Rising, 0, mx.DAQmx_Val_CountUp)
mx.DAQmxSetCICountEdgesTerm(ci_task, "ni6363/ctr0", "/ni6363/RTSI7")
mx.DAQmxStartTask(ci_task)
time.sleep(2)
mx.DAQmxReadCounterScalarU32(ci_task, 1.0, byref(count), None)

mx.DAQmxStopTask(ci_task)
mx.DAQmxClearTask(ci_task)
mx.DAQmxStopTask(ao_task)
mx.DAQmxClearTask(ao_task)

if count.value > 100:
    print(f"RTSI7 working: {count.value} edges in 2s")
else:
    print(f"RTSI7 NOT working: only {count.value} edges in 2s")
