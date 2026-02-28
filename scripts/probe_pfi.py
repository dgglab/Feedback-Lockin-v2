"""Probe which PFI pin on the 6363 receives the clock from the 6738.

Starts an AO task on the 6738, exports its sample clock to PFI7,
then counts edges on each PFI pin (0-15) on the 6363 for 2 seconds.
Whichever pin shows counts is physically connected.

Usage: uv run python scripts/probe_pfi.py
"""
from ctypes import byref, c_int32, c_uint32
import time
import numpy as np
import PyDAQmx as mx

OUTPUT_DEV = "ni6738"
INPUT_DEV = "ni6363"
OUTPUT_PFI = 7
FREQ = 1000.0  # Simple 1kHz clock for easy counting
NPOINTS = 100
DURATION = 2.0  # seconds to count

print(f"Setting up AO task on {OUTPUT_DEV} with sample clock at {FREQ * NPOINTS} Hz...")

# Create and start an AO task to generate a sample clock
ao_task = mx.TaskHandle()
written = c_int32()
mx.DAQmxCreateTask("", byref(ao_task))
mx.DAQmxCreateAOVoltageChan(ao_task, f"{OUTPUT_DEV}/ao0", "",
        -10.0, 10.0, mx.DAQmx_Val_Volts, None)
mx.DAQmxCfgSampClkTiming(ao_task, "OnboardClock", FREQ * NPOINTS,
        mx.DAQmx_Val_Rising, mx.DAQmx_Val_ContSamps, NPOINTS)
mx.DAQmxExportSignal(ao_task, mx.DAQmx_Val_SampleClock,
        f"/{OUTPUT_DEV}/PFI{OUTPUT_PFI}")

# Write a sine wave and start
data = np.sin(2 * np.pi * np.arange(NPOINTS) / NPOINTS).astype(np.float64)
mx.DAQmxWriteAnalogF64(ao_task, NPOINTS, True, 10.0,
        mx.DAQmx_Val_GroupByChannel, data, byref(written), None)
print(f"AO task running, clock exported to /{OUTPUT_DEV}/PFI{OUTPUT_PFI}")

# Now count edges on each PFI of the input device
print(f"\nCounting edges on {INPUT_DEV}/PFI0-15 for {DURATION}s...")
print("-" * 40)

results = []
for pfi in range(16):
    ci_task = mx.TaskHandle()
    count = c_uint32()
    try:
        mx.DAQmxCreateTask("", byref(ci_task))
        mx.DAQmxCreateCICountEdgesChan(ci_task,
                f"{INPUT_DEV}/ctr0", "", mx.DAQmx_Val_Rising, 0,
                mx.DAQmx_Val_CountUp)
        mx.DAQmxSetCICountEdgesTerm(ci_task, f"{INPUT_DEV}/ctr0",
                f"/{INPUT_DEV}/PFI{pfi}")
        mx.DAQmxStartTask(ci_task)
        time.sleep(DURATION)
        mx.DAQmxReadCounterScalarU32(ci_task, 1.0, byref(count), None)
        mx.DAQmxStopTask(ci_task)
        mx.DAQmxClearTask(ci_task)
        results.append((pfi, count.value))
        marker = " <--- CONNECTED!" if count.value > 100 else ""
        print(f"  PFI{pfi:2d}: {count.value:>8d} edges{marker}")
    except Exception as e:
        mx.DAQmxClearTask(ci_task)
        results.append((pfi, -1))
        print(f"  PFI{pfi:2d}: ERROR - {e}")

# Cleanup
mx.DAQmxStopTask(ao_task)
mx.DAQmxClearTask(ao_task)

print("-" * 40)
connected = [(pfi, n) for pfi, n in results if n > 100]
if connected:
    print(f"\nFound clock on: {', '.join(f'PFI{p} ({n} edges)' for p, n in connected)}")
    print(f"Update vti.ini: input_clock_channel=/{INPUT_DEV}/PFI{connected[0][0]}")
else:
    print("\nNo clock detected on any PFI pin.")
    print("Check: is there a physical cable between the 6738 and 6363?")
