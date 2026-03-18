from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QListWidget, QTextEdit,
                             QGridLayout, QGroupBox, QScrollArea)

class MainWindow(QMainWindow):
    def __init__(self, ros_node, config):
        super().__init__()
        self.ros_node = ros_node
        self.config = config   # dictionary with bool_indicators, float_displays, buttons

        # Connect ROS signals to GUI slots
        self.ros_node.topic_list_updated.connect(self.update_topic_list)
        self.ros_node.topic_data_received.connect(self.display_topic_data)
        self.ros_node.bool_indicator_updated.connect(self.update_bool_indicator)
        self.ros_node.float_value_updated.connect(self.update_float_display)

        # Set up the UI
        self.setWindowTitle("USV Diagnostic GUI - Enhanced")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # ========== LEFT PANEL: Topic List ==========
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("ROS Topics (click to echo)"))
        self.topic_list = QListWidget()
        self.topic_list.itemClicked.connect(self.on_topic_clicked)
        left_layout.addWidget(self.topic_list)

        # Echo display area
        self.echo_display = QTextEdit()
        self.echo_display.setReadOnly(True)
        left_layout.addWidget(QLabel("Topic Echo:"))
        left_layout.addWidget(self.echo_display)

        # ========== RIGHT PANEL: Diagnostics ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # --- Bool Indicators Group ---
        if self.config.get('bool_indicators'):
            bool_group = QGroupBox("Status Indicators")
            bool_layout = QGridLayout()
            self.indicator_labels = {}   # topic -> (label_widget, circle_widget)
            row = 0
            for idx, item in enumerate(self.config['bool_indicators']):
                topic = item['topic']
                label_text = item.get('label', topic)
                # Create a colored circle (QLabel with stylesheet)
                circle = QLabel()
                circle.setFixedSize(20, 20)
                circle.setStyleSheet("background-color: gray; border-radius: 10px;")
                # Label
                lbl = QLabel(label_text)
                bool_layout.addWidget(circle, row, 0)
                bool_layout.addWidget(lbl, row, 1)
                self.indicator_labels[topic] = (lbl, circle)
                # Subscribe to this bool topic
                self.ros_node.add_bool_indicator(topic)
                row += 1
            bool_group.setLayout(bool_layout)
            right_layout.addWidget(bool_group)

        # --- Float Displays Group ---
        if self.config.get('float_displays'):
            float_group = QGroupBox("Sensor Values")
            float_layout = QGridLayout()
            self.float_labels = {}   # topic -> (label_widget, value_widget)
            row = 0
            for idx, item in enumerate(self.config['float_displays']):
                topic = item['topic']
                label_text = item.get('label', topic)
                unit = item.get('unit', '')
                # Description label
                desc_lbl = QLabel(label_text)
                # Value label
                value_lbl = QLabel("---")
                if unit:
                    value_lbl.setText(f"--- {unit}")
                float_layout.addWidget(desc_lbl, row, 0)
                float_layout.addWidget(value_lbl, row, 1)
                self.float_labels[topic] = (desc_lbl, value_lbl, unit)
                # Subscribe to this float topic
                self.ros_node.add_float_display(topic)
                row += 1
            float_group.setLayout(float_layout)
            right_layout.addWidget(float_group)

        # --- Buttons Group ---
        if self.config.get('buttons'):
            button_group = QGroupBox("Commands")
            button_layout = QHBoxLayout()
            for item in self.config['buttons']:
                topic = item['topic']
                label = item.get('label', topic)
                msg_type = item.get('msg_type', 'bool')
                value = item.get('value', True)
                btn = QPushButton(label)
                # Connect button to a lambda that calls the publish method
                btn.clicked.connect(lambda checked, t=topic, m=msg_type, v=value:
                                    self.ros_node.publish_bool(t, v))
                button_layout.addWidget(btn)
            button_group.setLayout(button_layout)
            right_layout.addWidget(button_group)

        # Add stretch to push everything up
        right_layout.addStretch()

        # ========== Combine left and right panels ==========
        main_layout.addWidget(left_panel, 1)   # left takes 1 part
        main_layout.addWidget(right_panel, 2)  # right takes 2 parts

        # Request initial topic list
        self.ros_node.refresh_topic_list()

    # -------------------- Slots --------------------
    @pyqtSlot(list)
    def update_topic_list(self, topics):
        self.topic_list.clear()
        self.topic_list.addItems(topics)

    @pyqtSlot(str, str)
    def display_topic_data(self, topic, data):
        self.echo_display.append(f"--- {topic} ---")
        self.echo_display.append(data)
        # Optionally limit number of lines
        doc = self.echo_display.document()
        if doc.lineCount() > 100:
            # Keep last 50 lines
            cursor = self.echo_display.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            cursor.movePosition(QtGui.QTextCursor.Down, QtGui.QTextCursor.KeepAnchor, 50)
            cursor.removeSelectedText()

    @pyqtSlot(str, bool)
    def update_bool_indicator(self, topic, value):
        if topic in self.indicator_labels:
            _, circle = self.indicator_labels[topic]
            color = "#00ff00" if value else "#ff0000"   # green if True, red if False
            circle.setStyleSheet(f"background-color: {color}; border-radius: 10px;")

    @pyqtSlot(str, float)
    def update_float_display(self, topic, value):
        if topic in self.float_labels:
            _, value_lbl, unit = self.float_labels[topic]
            if unit:
                value_lbl.setText(f"{value:.2f} {unit}")
            else:
                value_lbl.setText(f"{value:.2f}")

    @pyqtSlot()
    def on_topic_clicked(self, item):
        topic_name = item.text()
        self.ros_node.subscribe_to_topic_echo(topic_name)
        self.echo_display.append(f"Subscribed to {topic_name}...")