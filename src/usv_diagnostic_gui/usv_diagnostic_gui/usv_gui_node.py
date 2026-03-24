import importlib
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import Bool, Float32
from rosidl_runtime_py.utilities import get_message
from rosidl_runtime_py.convert import message_to_ordereddict
from PyQt5.QtCore import QObject, pyqtSignal

class UsvGuiNode(Node, QObject):
    topic_list_updated = pyqtSignal(list)
    topic_data_received = pyqtSignal(str, str)
    bool_indicator_updated = pyqtSignal(str, bool)
    float_value_updated = pyqtSignal(str, float)

    def __init__(self):
        Node.__init__(self, 'usv_gui_node')
        QObject.__init__(self)

        self.dynamic_subs = {}          # for topic echo
        self.indicator_subs = {}         # for bool indicators
        self.float_subs = {}              # for float displays
        self.button_publishers = {}       # for buttons

        self.create_timer(2.0, self.refresh_topic_list)

        self.get_logger().info('ROS GUI node initialized')

    def refresh_topic_list(self):
        # Get all topic names and emit signal.
        topics = self.get_topic_names_and_types()
        topic_names = [t for t, _ in topics]
        self.topic_list_updated.emit(topic_names)

    def subscribe_to_topic_echo(self, topic_name):
        # Remove all existing echo subscriptions
        for sub in self.dynamic_subs.values():
            self.destroy_subscription(sub)
        self.dynamic_subs.clear()

        topics = self.get_topic_names_and_types()
        topic_type = None
        for t, types in topics:
            if t == topic_name:
                topic_type = types[0]
                break
        if not topic_type:
            self.get_logger().warn(f'Could not find type for {topic_name}')
            return
        try:
            msg_module = get_message(topic_type)
        except Exception as e:
            msg = f"Cannot subscribe: {e}"
            self.get_logger().error(f'Failed to import {topic_type}: {e}')
            self.topic_data_received.emit(topic_name, msg)
            return

        # Use BEST_EFFORT so we can receive from sensor/nav publishers that don't use RELIABLE
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # Create subscription with lambda that includes topic name
        sub = self.create_subscription(
            msg_module,
            topic_name,
            lambda msg, tn=topic_name: self.dynamic_callback(msg, tn),
            qos
        )
        self.dynamic_subs[topic_name] = sub
        self.get_logger().info(f'Subscribed to {topic_name} ({topic_type})')

    def dynamic_callback(self, msg, topic_name):
        try:
            d = message_to_ordereddict(msg)
            msg_str = str(d)
        except Exception:
            msg_str = str(msg)
        self.topic_data_received.emit(topic_name, msg_str)

    def add_bool_indicator(self, topic_name):
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

    def add_float_display(self, topic_name):
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

    def publish_bool(self, topic_name, value):
        if topic_name not in self.button_publishers:
            self.button_publishers[topic_name] = self.create_publisher(Bool, topic_name, 10)
        msg = Bool()
        msg.data = value
        self.button_publishers[topic_name].publish(msg)
        self.get_logger().info(f'Published {value} to {topic_name}')
