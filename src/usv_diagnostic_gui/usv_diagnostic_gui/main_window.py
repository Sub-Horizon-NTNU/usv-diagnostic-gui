from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QListWidget, QTextEdit, QGroupBox, QScrollArea)
from PyQt5.QtWidgets import QListWidgetItem 

from usv_diagnostic_gui.diagnostic_widgets import (
    BoolIndicatorWidget, FloatDisplayWidget, CommandButtonWidget, HeartbeatIndicatorWidget
)

class MainWindow(QMainWindow):
    def __init__(self, ros_node, config):
        super().__init__()
        self.ros_node = ros_node

        self.ros_node.topic_list_updated.connect(self.update_topic_list)
        self.ros_node.topic_data_received.connect(self.display_topic_data)

        self.setWindowTitle("USV Diagnostic GUI")
        self.setGeometry(100, 100, 1920, 1200)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # ---------- Left panel: Topic list and echo ----------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("ROS Topics (click to echo)"))
        self.topic_list = QListWidget()
        self.topic_list.itemClicked.connect(self.on_topic_clicked)
        left_layout.addWidget(self.topic_list)

        self.echo_display = QTextEdit()
        self.echo_display.setReadOnly(True)
        left_layout.addWidget(QLabel("Topic Echo:"))
        left_layout.addWidget(self.echo_display)

        # ---------- Right panel: Diagnostics from config ----------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Create widget groups based on config
        self.widgets = []   # keep references to all diagnostic widgets

        if 'heartbeat_indicators' in config:
            columns = config['heartbeat_indicators'].get('columns', 1)
            items = config['heartbeat_indicators'].get('items', config['heartbeat_indicators'])
            group = self._create_group("Heartbeat Indicators", items, HeartbeatIndicatorWidget, columns)
            right_layout.addWidget(group)

        if 'bool_indicators' in config:
            columns = config['bool_indicators'].get('columns', 1)
            items = config['bool_indicators'].get('items', config['bool_indicators'])
            group = self._create_group("Status Indicators", items, BoolIndicatorWidget, columns)
            right_layout.addWidget(group)

        if 'float_displays' in config:
            columns = config['float_displays'].get('columns', 1)
            items = config['float_displays'].get('items', config['float_displays'])
            group = self._create_group("Sensor Values", items, FloatDisplayWidget, columns)
            right_layout.addWidget(group)

        if 'buttons' in config:
            columns = config['buttons'].get('columns', 1)
            items = config['buttons'].get('items', config['buttons'])
            group = self._create_group("Commands", items, CommandButtonWidget, columns)
            right_layout.addWidget(group)

        right_layout.addStretch()

        # Add left and right panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)

        # Request initial topic list
        self.ros_node.refresh_topic_list()

    def _create_group(self, title, items, widget_class, columns=1):
        group = QtWidgets.QGroupBox(title)
        layout = QtWidgets.QGridLayout()
        for index, spec in enumerate(items):
            row = index // columns
            col = index % columns
            widget_obj = widget_class(spec, parent=group)
            widget_obj.connect_signals(self.ros_node)
            self.widgets.append(widget_obj)
            layout.addWidget(widget_obj, row, col, 1, 1)
        group.setLayout(layout)
        return group

    @pyqtSlot(list)
    def update_topic_list(self, topics):
        self.topic_list.clear()
        self.topic_list.addItems(topics)

    @pyqtSlot(str, str)
    def display_topic_data(self, topic, data):
        self.echo_display.append(f"--- {topic} ---")
        self.echo_display.append(data)
        
    @pyqtSlot(QListWidgetItem)
    def on_topic_clicked(self, item):
        topic_name = item.text()
        self.echo_display.clear()
        self.ros_node.subscribe_to_topic_echo(topic_name)
        self.echo_display.append(f"Subscribed to {topic_name}...")