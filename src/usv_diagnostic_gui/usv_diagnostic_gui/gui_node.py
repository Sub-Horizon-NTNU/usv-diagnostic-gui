import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from PyQt5.QtCore import QObject, pyqtSignal

class RosNode(Node, QObject):
    # Signals to communicate with the GUI
    data_received = pyqtSignal(str)
    status_message = pyqtSignal(str)

    def __init__(self):
        Node.__init__(self, 'usv_gui_node')
        QObject.__init__(self)

        # Example subscriber
        self.subscription = self.create_subscription(
            String,
            '/diagnostic_status',   # You can change this topic
            self.listener_callback,
            10)
        self.subscription

        # Example publisher
        self.publisher = self.create_publisher(String, '/gui_command', 10)

        self.get_logger().info('ROS node initialized')

    def listener_callback(self, msg):
        # Emit signal with the received message
        self.data_received.emit(f"Received: {msg.data}")
        self.get_logger().info(f'Heard: {msg.data}')

    def publish_command(self, command_text):
        msg = String()
        msg.data = command_text
        self.publisher.publish(msg)
        self.status_message.emit(f"Published: {command_text}")