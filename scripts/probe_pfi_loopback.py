"""Loopback test: verify the 6738 is actually exporting its clock.

Exports the AO sample clock to PFI7 on the 6738, then counts edges
on the 6738's OWN PFI pins. If PFI7 shows edges, the export works
and the problem is physical wiring. If not, the export is broken.

Usage: uv run python scripts/probe_pfi_loopback.py
"""
from ctypes import byref, c_int32, c_uint32
import time
import numpy as np
import PyDAQmx as mx

DEV = "ni6738"
OUTPUT_PFI = 7
FREQ = 1000.0
NPOINTS = 100
DURATION = 2.0

print(f"Setting up AO task on {DEV}...")

ao_task = mx.TaskHandle()
written = c_int32()
mx.DAQmxCreateTask("", byref(ao_task))
mx.DAQmxCreateAOVoltageChan(ao_task, f"{DEV}/ao0", "",
        -10.0, 10.0, mx.DAQmx_Val_Volts, None)
mx.DAQmxCfgSampClkTiming(ao_task, "OnboardClock", FREQ * NPOINTS,
        mx.DAQmx_Val_Rising, mx.DAQmx_Val_ContSamps, NPOINTS)
mx.DAQmxExportSignal(ao_task, mx.DAQmx_Val_SampleClock,
        f"/{DEV}/PFI{OUTPUT_PFI}")

data = np.sin(2 * np.pi * np.arange(NPOINTS) / NPOINTS).astype(np.float64)
mx.DAQmxWriteAnalogF64(ao_task, NPOINTS, True, 10.0,
        mx.DAQmx_Val_GroupByChannel, data, byref(written), None)
print(f"AO task running, clock exported to /{DEV}/PFI{OUTPUT_PFI}")

print(f"\nCounting edges on {DEV}'s own PFI pins for {DURATION}s each...")
print("-" * 40)

results = []
for pfi in range(8):
    if pfi == OUTPUT_PFI:
        # Can't count on the same pin we're exporting to
        print(f"  PFI{pfi:2d}: (skipped - export pin)")
        continue
    ci_task = mx.TaskHandle()
    count = c_uint32()
    try:
        mx.DAQmxCreateTask("", byref(ci_task))
        mx.DAQmxCreateCICountEdgesChan(ci_task,
                f"{DEV}/ctr0", "", mx.DAQmx_Val_Rising, 0,
                mx.DAQmx_Val_CountUp)
        mx.DAQmxSetCICountEdgesTerm(ci_task, f"{DEV}/ctr0",
                f"/{DEV}/PFI{pfi}")
        mx.DAQmxStartTask(ci_task)
        time.sleep(DURATION)
        mx.DAQmxReadCounterScalarU32(ci_task, 1.0, byref(count), None)
        mx.DAQmxStopTask(ci_task)
        mx.DAQmxClearTask(ci_task)
        results.append((pfi, count.value))
        marker = " <--- signal!" if count.value > 100 else ""
        print(f"  PFI{pfi:2d}: {count.value:>8d} edges{marker}")
    except Exception as e:
        mx.DAQmxClearTask(ci_task)
        results.append((pfi, -1))
        print(f"  PFI{pfi:2d}: ERROR - {e}")

mx.DAQmxStopTask(ao_task)
mx.DAQmxClearTask(ao_task)

print("-" * 40)
has_signal = any(n > 100 for _, n in results)
if has_signal:
    print("\nExport is working. Problem is physical wiring to the 6363.")
else:
    print("\nNo edges seen even on the 6738 itself.")
    print("The ExportSignal may not be working on this device.")
