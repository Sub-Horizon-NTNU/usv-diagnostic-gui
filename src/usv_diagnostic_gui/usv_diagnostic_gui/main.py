#!/usr/bin/env python3
import sys
import threading
import rclpy
import yaml
import os

# Disable GPU acceleration for QtWebEngine (required inside distrobox/containers
# where GPU drivers like nouveau/DRI3 are not available to the Chromium process)
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu --disable-software-rasterizer')
from ament_index_python.packages import get_package_share_directory
from rclpy.executors import MultiThreadedExecutor
from PyQt5.QtWidgets import QApplication

from usv_diagnostic_gui.usv_gui_node import UsvGuiNode
from usv_diagnostic_gui.main_window import MainWindow

config_path = os.path.join(
    get_package_share_directory('usv_diagnostic_gui'),
    'config', 'config.yaml'
)
with open(config_path, 'r') as f:
    CONFIG = yaml.safe_load(f)

def spin_ros(executor):
    while rclpy.ok():
        executor.spin_once(timeout_sec=0.1)

def main(args=None):
    rclpy.init(args=args)

    ros_node = UsvGuiNode()
    executor = MultiThreadedExecutor()
    executor.add_node(ros_node)

    ros_thread = threading.Thread(target=spin_ros, args=(executor,), daemon=True)
    ros_thread.start()

    app = QApplication(sys.argv)

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

    window = MainWindow(ros_node, CONFIG)
    window.show()

    exit_code = app.exec_()
    rclpy.shutdown()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()