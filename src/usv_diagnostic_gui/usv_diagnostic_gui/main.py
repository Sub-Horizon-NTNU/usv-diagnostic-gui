#!/usr/bin/env python3
import sys
import threading
import rclpy
from rclpy.executors import MultiThreadedExecutor
from PyQt5.QtWidgets import QApplication

from usv_diagnostic_gui.ros_node import RosNode
from usv_diagnostic_gui.main_window import MainWindow

def spin_ros(executor):
    while rclpy.ok():
        try:
            executor.spin_once(timeout_sec=0.1)
        except Exception as e:
            print(f"Error in ROS spin: {e}")

def main(args=None):
    rclpy.init(args=args)

    # Configuration for diagnostic displays
    config = {
        'bool_indicators': [
            {'topic': '/diagnostic/status', 'label': 'System Status'},
            {'topic': '/motor/active', 'label': 'Motor Active'},
            {'topic': '/connection/ok', 'label': 'Connection OK'},
        ],
        'float_displays': [
            {'topic': '/battery/voltage', 'label': 'Battery Voltage', 'unit': 'V'},
            {'topic': '/temperature/cpu', 'label': 'CPU Temperature', 'unit': '°C'},
            {'topic': '/depth/current', 'label': 'Depth', 'unit': 'm'},
        ],
        'buttons': [
            {'topic': '/cmd/start', 'msg_type': 'bool', 'value': True, 'label': 'Start'},
            {'topic': '/cmd/stop', 'msg_type': 'bool', 'value': False, 'label': 'Stop'},
            {'topic': '/cmd/reset', 'msg_type': 'bool', 'value': True, 'label': 'Reset'},
        ]
    }

    # Create ROS node
    ros_node = RosNode()

    # Use MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    executor.add_node(ros_node)

    # Start ROS spinning thread
    ros_thread = threading.Thread(target=spin_ros, args=(executor,), daemon=True)
    ros_thread.start()

    # Create Qt application
    app = QApplication(sys.argv)

    # Apply a modern style sheet (optional)
    app.setStyleSheet("""
        QMainWindow { background-color: #2b2b2b; }
        QLabel { color: #ffffff; }
        QGroupBox {
            color: #ffffff;
            border: 2px solid #555;
            border-radius: 5px;
            margin-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #555;
            padding: 8px;
            border-radius: 4px;
        }
        QPushButton:hover { background-color: #4a4a4a; }
        QListWidget, QTextEdit {
            background-color: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid #3f3f3f;
        }
    """)

    # Create and show main window
    window = MainWindow(ros_node, config)
    window.show()

    # Run Qt event loop
    exit_code = app.exec_()

    # Cleanup
    rclpy.shutdown()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()