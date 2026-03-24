from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot, QTimer


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
                self.value_label.setText(f"{value:.2f} {self.unit}")
            else:
                self.value_label.setText(f"{value:.2f}")
            self.timer.start()

    def connect_signals(self, ros_node):
        ros_node.add_float_display(self.topic)
        ros_node.float_value_updated.connect(self.on_float_updated)


class CommandButtonWidget(QtWidgets.QWidget):
    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.topic = spec['topic']
        self.value = spec.get('value', True)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.button = QtWidgets.QPushButton(spec.get('label', spec['topic']))
        self.button.clicked.connect(self.on_clicked)
        layout.addWidget(self.button)

        layout.addStretch()

    def on_clicked(self):
        if hasattr(self, 'ros_node'):
            self.ros_node.publish_bool(self.topic, self.value)

    def connect_signals(self, ros_node):
        self.ros_node = ros_node