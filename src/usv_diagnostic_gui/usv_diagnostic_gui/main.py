#!/usr/bin/env python3
import sys
import threading
import rclpy
from rclpy.executors import MultiThreadedExecutor
from PyQt5.QtWidgets import QApplication

from usv_diagnostic_gui.gui_node import RosNode
from usv_diagnostic_gui.main_window import MainWindow

def spin_ros(executor):
    """Run the ROS executor in a separate thread."""
    while rclpy.ok():
        try:
            executor.spin_once(timeout_sec=0.1)
        except Exception as e:
            print(f"Error in ROS spin: {e}")

def main(args=None):
    rclpy.init(args=args)

    ros_node = RosNode()

    executor = MultiThreadedExecutor()
    executor.add_node(ros_node)

    ros_thread = threading.Thread(target=spin_ros, args=(executor,), daemon=True)
    ros_thread.start()

    app = QApplication(sys.argv)

    window = MainWindow(ros_node)
    window.show()

    exit_code = app.exec_()

    rclpy.shutdown()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()