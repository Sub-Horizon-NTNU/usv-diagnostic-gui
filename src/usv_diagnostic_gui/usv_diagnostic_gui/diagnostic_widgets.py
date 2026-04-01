from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QTimer
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QLabel, QVBoxLayout


class GpsStatusBar(QtWidgets.QWidget):
    """Compact horizontal GPS status strip shown above the map."""

    TIMEOUT_MS = 2000

    _RTK_MAP = {
        0: ('No Fix',    '#ff0000'),
        1: ('GPS',       '#ff8800'),
        2: ('SBAS',      '#ffcc00'),
        4: ('RTK Fixed', '#00ff00'),
        5: ('RTK Float', '#aaff00'),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        self._rtk_dot, self._rtk_val = self._item(lay)
        self._rtk_timer = self._timer(lambda: self._reset(self._rtk_dot, self._rtk_val))
        self._sep(lay)

        self._ntrip_dot, self._ntrip_val = self._item(lay, 'NTRIP')
        self._ntrip_timer = self._timer(lambda: self._reset(self._ntrip_dot, self._ntrip_val))
        self._sep(lay)

        self._snr_dot, self._snr_val = self._item(lay, 'Signal')
        self._snr_timer = self._timer(lambda: self._reset(self._snr_dot, self._snr_val))
        self._sep(lay)

        self._stdlat_dot, self._stdlat_val = self._item(lay, 'Std Lat')
        self._stdlat_timer = self._timer(lambda: self._reset(self._stdlat_dot, self._stdlat_val))
        self._sep(lay)

        self._stdlon_dot, self._stdlon_val = self._item(lay, 'Std Lon')
        self._stdlon_timer = self._timer(lambda: self._reset(self._stdlon_dot, self._stdlon_val))
        self._sep(lay)

        self._tx_dot, self._tx_val = self._item(lay, 'To USV')
        self._tx_timer = self._timer(lambda: self._reset(self._tx_dot, self._tx_val), ms=6000)
        self._sep(lay)

        self._rx_dot, self._rx_val = self._item(lay, 'From USV')
        self._rx_timer = self._timer(lambda: self._reset(self._rx_dot, self._rx_val), ms=6000)
        self._sep(lay)

        self._sig_dot, self._sig_val = self._item(lay, 'Signal (Link)')
        self._sig_timer = self._timer(lambda: self._reset(self._sig_dot, self._sig_val), ms=6000)

        lay.addStretch()

    def _dot(self, color='#555555'):
        w = QtWidgets.QLabel()
        w.setFixedSize(20, 20)
        w.setStyleSheet(f"background-color:{color}; border-radius:10px;")
        return w

    def _item(self, lay, label=''):
        dot = self._dot()
        val = QtWidgets.QLabel('--')
        lay.addWidget(dot)
        if label:
            lay.addWidget(QtWidgets.QLabel(label))
        lay.addWidget(val)
        return dot, val

    def _sep(self, lay):
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.VLine)
        s.setStyleSheet('color: #444444;')
        lay.addWidget(s)

    def _timer(self, cb, ms=None):
        t = QTimer(self)
        t.setSingleShot(True)
        t.setInterval(ms if ms is not None else self.TIMEOUT_MS)
        t.timeout.connect(cb)
        return t

    def _dot_color(self, dot, color):
        dot.setStyleSheet(f"background-color:{color}; border-radius:10px;")

    def _reset(self, dot, val):
        self._dot_color(dot, '#555555')
        val.setText('--')

    def connect_signals(self, ros_node):
        ros_node.add_float_display('septentrio/rtk_fix')
        ros_node.add_float_display('septentrio/snr_avg')
        ros_node.add_float_display('septentrio/std_lat')
        ros_node.add_float_display('septentrio/std_lon')
        ros_node.add_float_display('mikrotik/land/tx_mbps')
        ros_node.add_float_display('mikrotik/land/rx_mbps')
        ros_node.add_float_display('mikrotik/land/signal_dbm')
        ros_node.add_bool_indicator('septentrio/ntrip_active')
        ros_node.float_value_updated.connect(self._on_float)
        ros_node.bool_indicator_updated.connect(self._on_bool)

    @pyqtSlot(str, float)
    def _on_float(self, topic, value):
        if topic == 'septentrio/rtk_fix':
            text, color = self._RTK_MAP.get(int(value), ('Unknown', '#555555'))
            self._dot_color(self._rtk_dot, color)
            self._rtk_val.setText(text)
            self._rtk_timer.start()
        elif topic == 'septentrio/snr_avg':
            self._dot_color(self._snr_dot, '#0088ff')
            self._snr_val.setText(f'{value:.1f} dB-Hz')
            self._snr_timer.start()
        elif topic == 'septentrio/std_lat':
            self._dot_color(self._stdlat_dot, '#0088ff')
            self._stdlat_val.setText(f'{value:.3f} m')
            self._stdlat_timer.start()
        elif topic == 'septentrio/std_lon':
            self._dot_color(self._stdlon_dot, '#0088ff')
            self._stdlon_val.setText(f'{value:.3f} m')
            self._stdlon_timer.start()
        elif topic == 'mikrotik/land/tx_mbps':
            self._dot_color(self._tx_dot, '#0088ff')
            self._tx_val.setText(self._fmt_mbps(value))
            self._tx_timer.start()
        elif topic == 'mikrotik/land/rx_mbps':
            self._dot_color(self._rx_dot, '#0088ff')
            self._rx_val.setText(self._fmt_mbps(value))
            self._rx_timer.start()
        elif topic == 'mikrotik/land/signal_dbm':
            self._dot_color(self._sig_dot, '#0088ff')
            self._sig_val.setText(f'{value:.0f} dBm')
            self._sig_timer.start()

    @staticmethod
    def _fmt_mbps(value):
        if value >= 1.0:
            return f'{value:.1f} Mbps'
        return f'{value * 1000:.0f} kbps'

    @pyqtSlot(str, bool)
    def _on_bool(self, topic, value):
        if topic == 'septentrio/ntrip_active':
            self._dot_color(self._ntrip_dot, '#00cc55' if value else '#cc0000')
            self._ntrip_val.setText('Active' if value else 'Inactive')
            self._ntrip_timer.start()


class HeartbeatIndicatorWidget(QtWidgets.QWidget):
    TIMEOUT_MS = 2000

    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.topic = spec['topic']

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.circle = QtWidgets.QLabel()
        self.circle.setFixedSize(20, 20)
        self._set_red()
        layout.addWidget(self.circle)

        label_text = spec.get('label', spec['topic'])
        self.label = QtWidgets.QLabel(label_text)
        layout.addWidget(self.label)

        layout.addStretch()

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.TIMEOUT_MS)
        self.timer.timeout.connect(self._set_red)

    def _set_red(self):
        self.circle.setStyleSheet("background-color: #ff0000; border-radius: 10px;")

    def _set_green(self):
        self.circle.setStyleSheet("background-color: #00ff00; border-radius: 10px;")

    @pyqtSlot(str, bool)
    def on_bool_updated(self, topic, value):
        if topic == self.topic and value:
            self._set_green()
            self.timer.start()

    def connect_signals(self, ros_node):
        ros_node.add_bool_indicator(self.topic)
        ros_node.bool_indicator_updated.connect(self.on_bool_updated)


class BoolIndicatorWidget(QtWidgets.QWidget):
    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.topic = spec['topic']

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.circle = QtWidgets.QLabel()
        self.circle.setFixedSize(20, 20)
        self.circle.setStyleSheet("background-color: gray; border-radius: 10px;")
        layout.addWidget(self.circle)

        label_text = spec.get('label', spec['topic'])
        self.label = QtWidgets.QLabel(label_text)
        layout.addWidget(self.label)

        layout.addStretch()

    @pyqtSlot(str, bool)
    def on_bool_updated(self, topic, value):
        if topic == self.topic:
            color = "#00ff00" if value else "#ff0000"
            self.circle.setStyleSheet(f"background-color: {color}; border-radius: 10px;")

    def connect_signals(self, ros_node):
        ros_node.add_bool_indicator(self.topic)
        ros_node.bool_indicator_updated.connect(self.on_bool_updated)


class FloatDisplayWidget(QtWidgets.QWidget):
    TIMEOUT_MS = 2000

    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.topic = spec['topic']
        self.unit = spec.get('unit', '')

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label_text = spec.get('label', spec['topic'])
        self.desc_label = QtWidgets.QLabel(label_text)
        layout.addWidget(self.desc_label)

        self.value_label = QtWidgets.QLabel("---")
        layout.addWidget(self.value_label)

        layout.addStretch()

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.TIMEOUT_MS)
        self.timer.timeout.connect(lambda: self.value_label.setText("---"))

    @pyqtSlot(str, float)
    def on_float_updated(self, topic, value):
        if topic == self.topic:
            if self.unit:
                self.value_label.setText(f"{value:.1f} {self.unit}")
            else:
                self.value_label.setText(f"{value:.1f}")
            self.timer.start()

    def connect_signals(self, ros_node):
        ros_node.add_float_display(self.topic)
        ros_node.float_value_updated.connect(self.on_float_updated)


class LaunchArgsDialog(QDialog):
    def __init__(self, args: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Launch Arguments")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog        { background-color: #2b2b2b; color: #ffffff; }
            QLabel         { color: #ffffff; }
            QLineEdit      { background-color: #1e1e1e; color: #d4d4d4;
                             border: 1px solid #3f3f3f; padding: 4px; border-radius: 3px; }
            QDialogButtonBox QPushButton {
                background-color: #3c3c3c; color: white;
                border: 1px solid #555; padding: 6px 16px; border-radius: 4px; }
            QDialogButtonBox QPushButton:hover { background-color: #4a4a4a; }
        """)

        self._fields: dict[str, QLineEdit] = {}

        outer = QVBoxLayout(self)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        for arg in args:
            name = arg['name']
            default = str(arg.get('default', ''))
            description = arg.get('description', '')

            field = QLineEdit(default)
            if arg.get('secret', False):
                field.setEchoMode(QLineEdit.Password)
            label_text = name
            if description:
                label_text += f'\n  {description}'
            form.addRow(QLabel(label_text), field)
            self._fields[name] = field

        outer.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def get_args(self) -> dict[str, str]:
        return {name: field.text() for name, field in self._fields.items()}


class CommandButtonWidget(QtWidgets.QWidget):
    open_tab_requested = pyqtSignal(str)  # tab_name

    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.command = spec.get('command', '')
        self.tab_name = spec.get('tab_name', spec.get('label', 'Process'))
        self._args = spec.get('args', [])

        self._ros_node = None
        self._no_stop = spec.get('no_stop', False)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = spec.get('label', self.tab_name)
        self.start_btn = QtWidgets.QPushButton(label)
        self.start_btn.clicked.connect(self._on_start)
        layout.addWidget(self.start_btn)

        if not self._no_stop:
            self.stop_btn = QtWidgets.QPushButton('Stop')
            self.stop_btn.setEnabled(False)
            self.stop_btn.setStyleSheet("QPushButton:enabled { background-color: #8b0000; color: white; }")
            self.stop_btn.clicked.connect(self._on_stop)
            layout.addWidget(self.stop_btn)
        else:
            self.stop_btn = None

        layout.addStretch()

    def connect_signals(self, ros_node):
        self._ros_node = ros_node
        ros_node.command_done.connect(self._on_command_done)

    def _on_start(self):
        if not self._ros_node:
            return

        command = self.command

        if self._args:
            dialog = LaunchArgsDialog(self._args, parent=self)
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return
            arg_values = dialog.get_args()
            # Substitute {arg_name} placeholders in-place (e.g. passwords, inline values)
            for k, v in arg_values.items():
                command = command.replace(f'{{{k}}}', v)
            # Append remaining args as key:=value (ROS2 launch args)
            suffix = ' '.join(
                f'{k}:={v}' for k, v in arg_values.items()
                if f'{{{k}}}' not in self.command and v != ''
            )
            if suffix:
                command = f'{command} {suffix}'

        if not self._no_stop:
            self.open_tab_requested.emit(self.tab_name)
        self._ros_node.send_command(command, self.tab_name)
        self.start_btn.setEnabled(False)
        if self.stop_btn:
            self.stop_btn.setEnabled(True)

    def _on_stop(self):
        if not self._ros_node:
            return
        self._ros_node.cancel_command(self.tab_name)

    @pyqtSlot(str, int)
    def _on_command_done(self, tab_name: str, _exit_code: int):
        if tab_name == self.tab_name:
            self.start_btn.setEnabled(True)
            if self.stop_btn:
                self.stop_btn.setEnabled(False)
