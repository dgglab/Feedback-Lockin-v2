# Feedback Lockin V2

## How to use

Each output channel can have feedback either off or on. If feedback is off,
you are free to set the amplitude of the output sine curve yourself. This mode
mimics a standard lockin amplifier. If feedback is on, you instead set your
preferred setpoint. Then, the lockin will try to hold the corresponding input
channel at that setpoint by adjusting the output amplitude for you. This can
virtually ground contacts, such that you can measure current flowing into them
while holding them at fixed potentials.

## Requirements

PySide2, pyqtgraph, PyDAQmx

## How to run

Run with `python -m feedbacklockin`.

Optionally provide `-s path/to/config.ini`. For instance, to run locally with
no DAQ card, run `python -m feedbacklockin -s dev.ini`, and to run with the VTI
config, use `python -m feedbacklockin -s vti.ini`.

## Code Overview

The code is located in the `feedbacklockin` package. We loosely follow PEP8.

`main.py` creates the main window GUI and ties all the controls to the
underlying `FeedbackLockin` object (defined in `fbl.py`), which does the heavy
lifting. It also initializes the DAQ card and starts up a TCP server if
enabled.

`fbl.py` tracks the state of the lockin. Its most important methods are
`sine_out`, which computes the output voltages for the DAQ (`sin_outs.py`), and
`read_in`, which computes the next iteration of results given output from the
DAQ. The actual amplitude calculations are in `lockin_calc.py`, averaging is in
`moving_averager.py`, and feedback is in `discrete_pi.py` and
`bias_resistor.py`.

`daq.py` and `dummy_daq.py` should have the same interface. These write out
sine curves to the DAQ cards and read in results. `dummy_daq.py` uses a
simulated transfer matrix (`tmm.py`) rather than talking to real hardware.
