import argparse
from functools import partial
import math
import sys
import time

import numpy as np
import PySide2
from PySide2.QtCore import *
from PySide2.QtWidgets import *
import pyqtgraph as pg

from feedbacklockin import fbl
from feedbacklockin import server


class DoubleEdit(QDoubleSpinBox):
    """DoubleEdit is a QDoubleSpinBox with a few handy defaults."""
    def __init__(self, initial=0.0, read_only=False, clamp=(-10, 10)):
        QDoubleSpinBox.__init__(self)
        self.setRange(*clamp)
        self.setDecimals(3)
        self.setValue(initial)
        self.setReadOnly(read_only)
        if read_only:
            self.setFocusPolicy(Qt.NoFocus)
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.setCorrectionMode(QAbstractSpinBox.CorrectToPreviousValue)


class MainWindow(QMainWindow):

    # This will fire shortly before the program exits. Use it to clean up any
    # threads and sockets!
    exit = Signal()

    def __init__(self, settings):
        QMainWindow.__init__(self)
        self.setWindowTitle("Feedback Lockin")

        self._channels = int(settings.value('DAQ/channels', 8))
        self._freq = float(settings.value('FBL/frequency', 17.76))
        points = int(settings.value('FBL/points', 0))
        max_rate = int(settings.value('FBL/max_rate', 10000))
        if points == 0:
            self._npoints = int(max_rate / self._freq * 0.099) * 10
        else:
            self._npoints = points
        self._fbl = fbl.FeedbackLockin(self._channels, self._npoints)
        self._init_layout()
        self._ki.setValue(float(settings.value('FBL/ki', 0.01)))
        self._kp.setValue(float(settings.value('FBL/kp', 0.0)))
        self._averaging.setValue(int(settings.value('FBL/averaging', 1)))
        self._updates_since_fps = 0
        self._freq_timer = QElapsedTimer()

        self._update_k()

        if settings.value('DAQ/dummy', 'true').lower() == 'true':
            from feedbacklockin.dummy_daq import Daq
        else:
            from feedbacklockin.daq import Daq
        self._daq = Daq(self._channels, self._npoints)

        ics = settings.value('DAQ/input_channels', '')
        ocs = settings.value('DAQ/output_channels', '')
        if isinstance(ics, list): ics = ','.join(ics)
        if isinstance(ocs, list): ocs = ','.join(ocs)
        self._daq.set_channels(ics, ocs)

        oc = settings.value('DAQ/output_clock', '')
        occhan = settings.value('DAQ/output_clock_channel', '')
        icchan = settings.value('DAQ/input_clock_channel', '')
        self._daq.set_clocks(oc, occhan, icchan)

        self._daq.set_frequency(self._freq)
        self.exit.connect(self._daq.stop)
        self._daq.data_ready.connect(self._update)
        self._daq.init_daq()

        # Now make the TCP server if enabled.
        if settings.value('TCP/enabled', 'false').lower() == 'true':
            port = int(settings.value('TCP/port', 0))
            self._server = server.Server(port)
            self.exit.connect(self._server.close)
            self._server.send_data.connect(self._send_data)
            self._server.set_v.connect(self._set_v)
            self._server.set_i.connect(self._set_i)
            self._server.set_ki.connect(self._set_ki)
            self._server.set_feed.connect(self._set_feed)
            self._server.autotune.connect(self._fbl.autotune_pid)
            self._server.reset_avg.connect(self._fbl.reset_avg)

    def start(self):
        self._daq.start()
        self._freq_timer.start()

    def _send_data(self, conn):
        """Send FBL data to the supplied connection."""
        conn.write(np.concatenate((
            self._fbl.vOuts,
            self._fbl.vIns,
            self._fbl.X,
            self._fbl.P,
            self._fbl.DC)).tobytes('F'))

    def _set_v(self, chan, v):
        self._setpt_outs[chan].setValue(v)
        self._fbl.update_setpoint(v, chan)

    def _set_i(self, chan, v):
        self._amp_outs[chan].setValue(v)
        self._update_amps(chan)

    def _set_ki(self, v):
        self._ki.setValue(v)
        self._update_k()

    def _set_feed(self, chan, feed):
        self._fb_enabled[chan].setChecked(feed)
        self._set_feedback(chan, None)

    def _update(self):
        """Perform one iteration of feedback."""
        self._daq.set_output(self._fbl.sine_out())
        data = self._daq.get_input()
        self._fbl.read_in(data)

        for i in range(self._channels):
            self._v_ins[i].setValue(self._fbl.X[i])
            self._p_ins[i].setValue(self._fbl.P[i])
            if self._plot_enabled[i].isChecked():
                self._plot_items[i].setData(self._fbl.data[:, i])
            if self._fb_enabled[i].isChecked():
                self._amp_outs[i].setValue(self._fbl.vOuts[i])

        self._updates_since_fps += 1
        elapsed = self._freq_timer.elapsed()
        if elapsed > 1000:
            self._freq_timer.restart()
            self._freq_meas_spinbox.setValue(1000.0 / elapsed * self._updates_since_fps)
            self._updates_since_fps = 0

    def _zero_all(self):
        for i in range(self._channels):
            self._set_feed(i, False)
            self._set_v(i, 0.0)
            self._set_i(i, 0.0)

    def _update_setpoint(self, channel):
        self._fbl.update_setpoint(self._setpt_outs[channel].value(), channel)

    def _update_amps(self, channel):
        if not self._fb_enabled[channel].isChecked():
            self._fbl.update_amps(self._amp_outs[channel].value(), channel)

    def _update_k(self):
        self._fbl.update_k(self._ki.value(), self._kp.value())

    def _update_averaging(self):
        self._fbl.update_averaging(self._averaging.value())

    def _set_plot_enabled(self, channel, _):
        if self._plot_enabled[channel].isChecked():
            self._pw.getPlotItem().addItem(self._plot_items[channel])
        else:
            self._pw.getPlotItem().removeItem(self._plot_items[channel])

    def _set_feedback(self, channel, _):
        enabled = self._fb_enabled[channel].isChecked()
        self._fbl.set_feedback_enabled(channel, enabled)
        self._amp_outs[channel].setEnabled(not enabled)

    def _set_ref(self, text):
        if text == 'None':
            self._fbl.set_reference(None)
        else:
            self._fbl.set_reference(int(text))

    def _init_layout(self):
        """Make the GUI and hook up the appropriate signals/slots."""
        central_widget = QWidget()
        layout = QVBoxLayout()

        top_half = QHBoxLayout()
        self._pw = pg.PlotWidget()
        self._pw.setMinimumSize(600, 400)
        self._pw.getPlotItem().setRange(yRange=(-10, 10))
        self._pw.getPlotItem().hideButtons()
        self._pw.getPlotItem().showAxis('bottom', False)
        self._plot_items = []
        for i in range(self._channels):
            self._plot_items.append(self._pw.getPlotItem().plot(pen=i))
        top_half.addWidget(self._pw)

        in_box = QGroupBox("Inputs")
        in_box.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        in_layout = QGridLayout()
        in_box.setLayout(in_layout)

        self._v_ins = []
        self._plot_enabled = []
        self._p_ins = []
        for i in range(math.ceil(self._channels / 8)):
            in_layout.addWidget(QLabel('Channel'), i*3, 0)
            in_layout.addWidget(QLabel('Voltage'), i*3 + 1, 0)
            in_layout.addWidget(QLabel('Phase'), i*3 + 2, 0)
            for j in range(min(self._channels - i*3, 8)):
                chan = i*8 + j
                chan_layout = QHBoxLayout()
                chan_layout.addWidget(QLabel(f'{chan}'))
                pe = QCheckBox()
                pe.stateChanged.connect(partial(self._set_plot_enabled, chan))
                self._plot_enabled.append(pe)
                chan_layout.addWidget(pe)
                in_layout.addLayout(chan_layout, i*3, j + 1)
                v_in = DoubleEdit(read_only=True)
                self._v_ins.append(v_in)
                in_layout.addWidget(v_in, i*3 + 1, j + 1)
                p_in = DoubleEdit(read_only=True, clamp=(-180, 180))
                self._p_ins.append(p_in)
                in_layout.addWidget(p_in, i*3 + 2, j + 1)
        top_half.addWidget(in_box)
        layout.addLayout(top_half)

        bottom_half = QHBoxLayout()

        out_box = QGroupBox("Outputs")
        out_box.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        out_layout = QGridLayout()
        out_box.setLayout(out_layout)

        self._amp_outs = []
        self._setpt_outs = []
        self._fb_enabled = []
        for i in range(math.ceil(self._channels / 8)):
            out_layout.addWidget(QLabel('Channel'), i*3, 0)
            out_layout.addWidget(QLabel('Amplitude'), i*3 + 1, 0)
            out_layout.addWidget(QLabel('Setpoint'), i*3 + 2, 0)
            for j in range(min(self._channels - i*8, 8)):
                chan = i*8 + j
                out_layout.addWidget(QLabel(f'{chan}'), i*3, j + 1)
                v_out = DoubleEdit()
                v_out.editingFinished.connect(partial(self._update_amps, chan))
                self._amp_outs.append(v_out)
                out_layout.addWidget(v_out, i*3 + 1, j + 1)
                fb_layout = QHBoxLayout()
                fb_out = DoubleEdit()
                fb_out.editingFinished.connect(partial(self._update_setpoint, chan))
                self._setpt_outs.append(fb_out)
                fb_layout.addWidget(fb_out)
                fb_enabled = QCheckBox()
                fb_enabled.stateChanged.connect(partial(self._set_feedback, chan))
                self._fb_enabled.append(fb_enabled)
                fb_layout.addWidget(fb_enabled)
                out_layout.addLayout(fb_layout, i*3 + 2, j + 1)
        zero_button = QPushButton("Reset all")
        zero_button.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding))
        zero_button.clicked.connect(self._zero_all)
        out_layout.addWidget(zero_button, 0, 9, 3 * math.ceil(self._channels / 8), 1)

        settings_box = QGroupBox('Controls')
        settings_box.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        settings_layout = QGridLayout()
        settings_box.setLayout(settings_layout)

        settings_layout.addWidget(QLabel('Ki'), 0, 0)
        self._ki = DoubleEdit()
        self._ki.editingFinished.connect(self._update_k)
        settings_layout.addWidget(self._ki, 0, 1)
        settings_layout.addWidget(QLabel('Kp'), 1, 0)
        self._kp = DoubleEdit()
        self._kp.editingFinished.connect(self._update_k)
        settings_layout.addWidget(self._kp, 1, 1)

        settings_layout.addWidget(QLabel('Averaging'), 0, 2)
        self._avg_type = QComboBox()
        self._avg_type.addItems(['None', 'Sliding Window', 'Exponential'])
        self._avg_type.currentIndexChanged.connect(self._fbl.set_averaging_type)
        settings_layout.addWidget(self._avg_type, 0, 3)

        settings_layout.addWidget(QLabel('Amount'), 1, 2)
        self._averaging = QSpinBox()
        self._averaging.setMinimum(1)
        self._averaging.valueChanged.connect(self._update_averaging)
        settings_layout.addWidget(self._averaging, 1, 3)

        self._ref_in = QComboBox()
        self._ref_in.addItem('None')
        self._ref_in.addItems(list(map(str, range(self._channels))))
        self._ref_in.currentTextChanged.connect(self._set_ref)
        settings_layout.addWidget(QLabel('Ref in'), 1, 4)
        settings_layout.addWidget(self._ref_in, 1, 5)

        settings_layout.addWidget(QLabel('Frequency'), 0, 4)
        self._freq_spinbox = DoubleEdit(read_only=True, clamp=(0, 1000))
        self._freq_spinbox.setValue(self._freq)
        settings_layout.addWidget(self._freq_spinbox, 0, 5)

        status_box = QGroupBox('Status')
        status_box.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        status_layout = QGridLayout()
        status_box.setLayout(status_layout)
        status_layout.addWidget(QLabel('Frequency'), 0, 0)
        self._freq_meas_spinbox = DoubleEdit(read_only=True, clamp=(0, 1000))
        status_layout.addWidget(self._freq_meas_spinbox, 0, 1)

        status_layout.addWidget(QLabel('Samples'), 1, 0)
        self._samples_spinbox = QSpinBox()
        self._samples_spinbox.setReadOnly(True)
        self._samples_spinbox.setMinimum(2)
        self._samples_spinbox.setMaximum(10000)
        self._samples_spinbox.setValue(self._npoints)
        self._samples_spinbox.setButtonSymbols(QAbstractSpinBox.NoButtons)
        status_layout.addWidget(self._samples_spinbox, 1, 1)

        bottom_half.addWidget(out_box)
        botright = QVBoxLayout()
        botright.addWidget(settings_box)
        botright.addWidget(status_box)
        bottom_half.addLayout(botright)
        layout.addLayout(bottom_half)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)


def Main():
    options = argparse.ArgumentParser()
    options.add_argument('-s', '--settings', type=str,
                         default='dev.ini', help='Location of config ini.')
    options.add_argument('-v', '--version', action='store_true',
                         help='Print versions and exit.')
    args = options.parse_args()

    if args.version:
        print('PySide2 version:', PySide2.__version__)
        print('Qt version used to compile PySide2:', PySide2.QtCore.__version__)
        print('Local Qt version:', PySide2.QtCore.qVersion())
        sys.exit(0)

    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')

    app = QApplication(sys.argv)
    settings = QSettings(args.settings, QSettings.IniFormat)
    window = MainWindow(settings)
    app.aboutToQuit.connect(window.exit)
    window.start()
    window.show()

    sys.exit(app.exec_())
