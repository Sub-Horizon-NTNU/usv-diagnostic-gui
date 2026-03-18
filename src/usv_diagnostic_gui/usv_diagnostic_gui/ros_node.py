import importlib
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, String
from rosidl_runtime_py.utilities import get_message
from PyQt5.QtCore import QObject, pyqtSignal

class RosNode(Node, QObject):
    # Signals for GUI updates
    data_received = pyqtSignal(str)
    status_message = pyqtSignal(str)
    topic_list_updated = pyqtSignal(list)
    topic_data_received = pyqtSignal(str, str)   # (topic_name, data_string)
    bool_indicator_updated = pyqtSignal(str, bool)   # (topic_name, value)
    float_value_updated = pyqtSignal(str, float)     # (topic_name, value)

    def __init__(self):
        Node.__init__(self, 'usv_gui_node')
        QObject.__init__(self)

        # Example subscriber from MVP
        self.subscription = self.create_subscription(
            String,
            '/diagnostic_status',
            self.listener_callback,
            10)
        self.subscription

        # Example publisher from MVP
        self.publisher = self.create_publisher(String, '/gui_command', 10)

        # Dictionaries for dynamic features
        self.dynamic_subs = {}          # for topic echo
        self.indicator_subs = {}         # for bool indicators
        self.float_subs = {}              # for float displays
        self.button_publishers = {}       # for buttons (renamed to avoid conflict with base class)

        # Timer to refresh topic list every 2 seconds
        self.create_timer(2.0, self.refresh_topic_list)

        self.get_logger().info('ROS node initialized')

    # -------------------- Topic List --------------------
    def refresh_topic_list(self):
        """Get all topic names and emit signal."""
        topics = self.get_topic_names_and_types()
        topic_names = [t for t, _ in topics]
        self.topic_list_updated.emit(topic_names)

    # -------------------- Example MVP Callbacks --------------------
    def listener_callback(self, msg):
        self.data_received.emit(f"Received: {msg.data}")
        self.get_logger().info(f'Heard: {msg.data}')

    def publish_command(self, command_text):
        msg = String()
        msg.data = command_text
        self.publisher.publish(msg)
        self.status_message.emit(f"Published: {command_text}")

    # -------------------- Dynamic Topic Echo --------------------
    def subscribe_to_topic_echo(self, topic_name):
        """Subscribe to any topic to display its latest message."""
        # Remove old subscription if exists
        if topic_name in self.dynamic_subs:
            self.destroy_subscription(self.dynamic_subs[topic_name])
            del self.dynamic_subs[topic_name]

        # Get topic type
        topics = self.get_topic_names_and_types()
        topic_type = None
        for t, types in topics:
            if t == topic_name:
                topic_type = types[0]   # use first type
                break
        if not topic_type:
            self.get_logger().warn(f'Could not find type for {topic_name}')
            return

        # Dynamically import message type
        try:
            msg_module = get_message(topic_type)
        except Exception as e:
            self.get_logger().error(f'Failed to import {topic_type}: {e}')
            return

        # Create subscription with lambda that includes topic name
        sub = self.create_subscription(
            msg_module,
            topic_name,
            lambda msg, tn=topic_name: self.dynamic_callback(msg, tn),
            10
        )
        self.dynamic_subs[topic_name] = sub
        self.get_logger().info(f'Subscribed to {topic_name} ({topic_type})')

    def dynamic_callback(self, msg, topic_name):
        """Convert message to string and emit."""
        msg_str = str(msg)
        self.topic_data_received.emit(topic_name, msg_str)

    # -------------------- Bool Indicators --------------------
    def add_bool_indicator(self, topic_name):
        """Subscribe to a Bool topic for indicator light."""
        if topic_name in self.indicator_subs:
            return
        sub = self.create_subscription(
            Bool,
            topic_name,
            lambda msg, tn=topic_name: self.bool_callback(msg, tn),
            10
        )
        self.indicator_subs[topic_name] = sub

    def bool_callback(self, msg, topic_name):
        self.bool_indicator_updated.emit(topic_name, msg.data)

    # -------------------- Float Displays --------------------
    def add_float_display(self, topic_name):
        """Subscribe to a Float32 topic for numeric display."""
        if topic_name in self.float_subs:
            return
        sub = self.create_subscription(
            Float32,
            topic_name,
            lambda msg, tn=topic_name: self.float_callback(msg, tn),
            10
        )
        self.float_subs[topic_name] = sub

    def float_callback(self, msg, topic_name):
        self.float_value_updated.emit(topic_name, msg.data)

    # -------------------- Button Publishers --------------------
    def publish_bool(self, topic_name, value):
        """Publish a boolean value to a topic."""
        if topic_name not in self.button_publishers:
            self.button_publishers[topic_name] = self.create_publisher(Bool, topic_name, 10)
        msg = Bool()
        msg.data = value
        self.button_publishers[topic_name].publish(msg)
        self.get_logger().info(f'Published {value} to {topic_name}')