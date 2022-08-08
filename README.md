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

Python 3, numpy, PySide2, pyqtgraph, PyDAQmx

## Installation on windows

1. Install python 3 and git.
1. Run `pip install pipenv`.
1. `cd path/to/project`.
1. `pipenv install numpy pyside2 pydaqmx`.
1. `pipenv install -e git+https://github.com/pyqtgraph/pyqtgraph#egg=pyqtgraph`.
1. Run from here with `pipenv run python -m feedbacklockin`.

## How to run

Run with `python -m feedbacklockin` (don't forget pipenv if that's how you
installed it).

Optionally provide `-s path/to/config.ini`. For instance, to run locally with
no DAQ card, run `python -m feedbacklockin -s dev.ini`, and to run with the VTI
config, use `python -m feedbacklockin -s vti.ini`.

## TCP API

The lockin will start a TCP server listening on the supplied port, or a random
port if none is supplied. Connect to it and send commands to control the lockin
from external processes. Terminate each command with a newline. Spaces delimit
arguments.

* In response to `send_data`, the lockin will respond with output amplitudes,
X, and phase in an array with Fortran ordering.
* Send `set_setpoint CHANNEL VALUE` to set the feedback setpoint of the given
channel (integer) to the given value (float).
* Send `set_amplitude CHANNEL VALUE` to set the channel output amplitude if
feedback is off.
* Send `set_feedback CHANNEL ENABLED` to set the feedback setpoint. `ENABLED`
must be `0` for feedback disabled, and `1` for enabled.
* Send `autotune` to set PID constants.
* Send `reset_avg` to reset averaging.

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
