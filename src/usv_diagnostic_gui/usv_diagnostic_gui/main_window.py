from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QListWidget, QTextEdit, QGroupBox, QTabWidget,
                             QSplitter)
from PyQt5.QtWidgets import QListWidgetItem

from usv_diagnostic_gui.diagnostic_widgets import (
    BoolIndicatorWidget, FloatDisplayWidget, CommandButtonWidget,
    HeartbeatIndicatorWidget, GpsStatusBar
)
from usv_diagnostic_gui.map_widget import MapWidget
from usv_diagnostic_gui.camera_window import CameraWindow


class MainWindow(QMainWindow):
    def __init__(self, ros_node, config):
        super().__init__()
        self.ros_node = ros_node

        self.ros_node.topic_list_updated.connect(self.update_topic_list)
        self.ros_node.topic_data_received.connect(self.display_topic_data)
        self.ros_node.command_output.connect(self.on_command_output)
        self.ros_node.command_done.connect(self.on_command_done)

        self.setWindowTitle("USV Diagnostic GUI")
        self.setGeometry(100, 100, 1920, 1200)

        self._fs_btn = QtWidgets.QPushButton("⛶  Fullscreen")
        self._fs_btn.setCheckable(True)
        self._fs_btn.setToolTip("Fullscreen (Esc to exit)")
        self._fs_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #666666; padding: 2px 8px; }"
            "QPushButton:hover { color: #aaaaaa; }"
            "QPushButton:checked { color: #4a8abf; }"
        )
        self._fs_btn.clicked.connect(self._toggle_fullscreen)
        self.statusBar().addPermanentWidget(self._fs_btn)
        self.statusBar().setSizeGripEnabled(False)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("ROS Topics (click to echo)"))

        self.topic_list = QListWidget()
        self.topic_list.itemClicked.connect(self.on_topic_clicked)
        left_layout.addWidget(self.topic_list)

        self.output_tabs = QTabWidget()
        self.output_tabs.setTabsClosable(False)

        self.echo_display = QTextEdit()
        self.echo_display.setReadOnly(True)
        self.output_tabs.addTab(self.echo_display, "Topic Echo")

        left_layout.addWidget(self.output_tabs)

        self._process_tabs: dict[str, QTextEdit] = {}

        right_splitter = QSplitter(Qt.Vertical)

        diag_panel = QWidget()
        right_layout = QVBoxLayout(diag_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.widgets = []

        if 'heartbeat_indicators' in config:
            columns = config['heartbeat_indicators'].get('columns', 1)
            items = config['heartbeat_indicators'].get('items', [])
            group = self._create_group("Heartbeat Indicators", items, HeartbeatIndicatorWidget, columns)
            right_layout.addWidget(group)

        if 'bool_indicators' in config:
            columns = config['bool_indicators'].get('columns', 1)
            items = config['bool_indicators'].get('items', [])
            group = self._create_group("Status Indicators", items, BoolIndicatorWidget, columns)
            right_layout.addWidget(group)

        if 'float_displays' in config:
            columns = config['float_displays'].get('columns', 1)
            items = config['float_displays'].get('items', [])
            group = self._create_group("Sensor Values", items, FloatDisplayWidget, columns)
            right_layout.addWidget(group)

        if 'buttons' in config:
            columns = config['buttons'].get('columns', 1)
            items = config['buttons'].get('items', [])
            group = self._create_group("Commands", items, CommandButtonWidget, columns)
            right_layout.addWidget(group)

        gps_group = QGroupBox("GPS + Connection")
        gps_group_layout = QtWidgets.QVBoxLayout(gps_group)
        self._gps_bar = GpsStatusBar()
        self._gps_bar.connect_signals(ros_node)
        gps_group_layout.addWidget(self._gps_bar)

        right_layout.addWidget(gps_group)

        right_layout.addStretch()
        right_splitter.addWidget(diag_panel)

        self.map_widget = MapWidget()
        self.ros_node.gps_updated.connect(self.map_widget.update_position)
        right_splitter.addWidget(self.map_widget)

        self._camera_window = CameraWindow(ros_node)
        self._camera_window.show()

        right_splitter.setStretchFactor(0, 0)
        right_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_splitter, 2)

        self.ros_node.refresh_topic_list()

    def _toggle_fullscreen(self, checked):
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self._fs_btn.setChecked(False)
            self.showNormal()
        super().keyPressEvent(event)

    def _create_group(self, title, items, widget_class, columns=1):
        group = QtWidgets.QGroupBox(title)
        layout = QtWidgets.QGridLayout()
        for index, spec in enumerate(items):
            row = index // columns
            col = index % columns
            widget_obj = widget_class(spec, parent=group)
            widget_obj.connect_signals(self.ros_node)
            if isinstance(widget_obj, CommandButtonWidget):
                widget_obj.open_tab_requested.connect(self.open_process_tab)
            self.widgets.append(widget_obj)
            layout.addWidget(widget_obj, row, col, 1, 1)
        group.setLayout(layout)
        return group

    def open_process_tab(self, tab_name: str):
        if tab_name not in self._process_tabs:
            output = QTextEdit()
            output.setReadOnly(True)
            output.setFontFamily('monospace')
            self._process_tabs[tab_name] = output
            self.output_tabs.addTab(output, tab_name)

        for i in range(self.output_tabs.count()):
            if self.output_tabs.tabText(i) == tab_name:
                self.output_tabs.setCurrentIndex(i)
                break

    _MAX_LINES = 1000

    @staticmethod
    def _append_limited(text_edit: QTextEdit, text: str, max_lines: int):
        text_edit.moveCursor(text_edit.textCursor().End)
        text_edit.insertPlainText(text)
        doc = text_edit.document()
        while doc.blockCount() > max_lines:
            cursor = text_edit.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.BlockUnderCursor)
            cursor.movePosition(cursor.NextCharacter, cursor.KeepAnchor)
            cursor.removeSelectedText()
        text_edit.moveCursor(text_edit.textCursor().End)

    @pyqtSlot(str, str)
    def on_command_output(self, tab_name: str, line: str):
        output = self._process_tabs.get(tab_name)
        if output:
            self._append_limited(output, line, self._MAX_LINES)

    @pyqtSlot(str, int)
    def on_command_done(self, tab_name: str, _exit_code: int):
        for i in range(self.output_tabs.count()):
            if self.output_tabs.tabText(i) == tab_name:
                self.output_tabs.removeTab(i)
                break
        self._process_tabs.pop(tab_name, None)

    @pyqtSlot(list)
    def update_topic_list(self, topics):
        self.topic_list.clear()
        self.topic_list.addItems(topics)

    @pyqtSlot(str, str)
    def display_topic_data(self, topic, data):
        self._append_limited(self.echo_display, f"--- {topic} ---\n{data}\n", self._MAX_LINES)

    @pyqtSlot(QListWidgetItem)
    def on_topic_clicked(self, item):
        topic_name = item.text()
        self.echo_display.clear()
        self.ros_node.subscribe_to_topic_echo(topic_name)
        self.echo_display.append(f"Subscribed to {topic_name}...")
        self.output_tabs.setCurrentIndex(0)
