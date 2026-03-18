import sys
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QTextEdit

class MainWindow(QMainWindow):
    def __init__(self, ros_node):
        super().__init__()
        self.ros_node = ros_node

        # Connect ROS signals to GUI slots
        self.ros_node.data_received.connect(self.update_data_display)
        self.ros_node.status_message.connect(self.update_status)

        # Set up the UI
        self.setWindowTitle("USV Diagnostic GUI - MVP")
        self.setGeometry(100, 100, 600, 400)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Status display
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.status_display)

        # Data display
        self.data_display = QLabel("No data received yet.")
        self.data_display.setWordWrap(True)
        self.data_display.setStyleSheet("border: 1px solid gray; padding: 5px;")
        layout.addWidget(QLabel("Incoming Data:"))
        layout.addWidget(self.data_display)

        # Button to send a command
        self.send_button = QPushButton("Send Test Command")
        self.send_button.clicked.connect(self.on_send_clicked)
        layout.addWidget(self.send_button)

    @pyqtSlot(str)
    def update_data_display(self, message):
        self.data_display.setText(message)

    @pyqtSlot(str)
    def update_status(self, message):
        self.status_display.append(message)

    def on_send_clicked(self):
        # When button is clicked, publish a command via ROS node
        self.ros_node.publish_command("Test command from GUI")