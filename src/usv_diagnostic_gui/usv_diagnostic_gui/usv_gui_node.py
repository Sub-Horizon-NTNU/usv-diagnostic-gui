import math
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from rclpy.action import ActionClient
from std_msgs.msg import Bool, Float32, UInt16
from geographic_msgs.msg import GeoPoseStamped
from sensor_msgs.msg import NavSatFix, CompressedImage
from rosidl_runtime_py.utilities import get_message
from rosidl_runtime_py.convert import message_to_ordereddict
from PyQt5.QtCore import QObject, pyqtSignal

from usv_command_msgs.action import RunCommand


class UsvGuiNode(Node, QObject):
    topic_list_updated = pyqtSignal(list)
    topic_data_received = pyqtSignal(str, str)
    bool_indicator_updated = pyqtSignal(str, bool)
    float_value_updated = pyqtSignal(str, float)
    gps_updated = pyqtSignal(float, float, float)  # (latitude, longitude, heading_deg)
    gps_fix_updated = pyqtSignal(int)              # NavSatFix status code
    image_updated = pyqtSignal(bytes)              # JPEG bytes from camera
    command_output = pyqtSignal(str, str)          # (tab_name, line)
    command_done = pyqtSignal(str, int)            # (tab_name, exit_code)

    def __init__(self):
        Node.__init__(self, 'usv_gui_node')
        QObject.__init__(self)

        self.dynamic_subs = {}
        self.indicator_subs = {}
        self.float_subs = {}
        self.button_publishers = {}

        self._command_client = ActionClient(
            self, RunCommand, 'usv_command_node/run_command'
        )
        self._active_goals: dict[str, object] = {}  # tab_name -> goal_handle

        self._servo_pub = self.create_publisher(UInt16, '/camera/servo/pulse', 10)
        self._stream_paused_pub = self.create_publisher(Bool, '/camera/stream/paused', 10)
        self.create_subscription(
            CompressedImage,
            '/camera/image/compressed',
            self._image_callback,
            10,
        )

        self.create_timer(2.0, self.refresh_topic_list)

        gps_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.create_subscription(
            GeoPoseStamped,
            'ap/geopose/filtered',
            self._gps_callback,
            gps_qos
        )
        self.create_subscription(
            NavSatFix,
            'ap/navsat',
            self._navsat_callback,
            gps_qos
        )

        self.get_logger().info('ROS GUI node initialized')

    def refresh_topic_list(self):
        topics = self.get_topic_names_and_types()
        topic_names = [t for t, _ in topics]
        self.topic_list_updated.emit(topic_names)

    def subscribe_to_topic_echo(self, topic_name):
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

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
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

    def _image_callback(self, msg):
        self.image_updated.emit(bytes(msg.data))

    def set_stream_paused(self, paused: bool):
        msg = Bool()
        msg.data = paused
        self._stream_paused_pub.publish(msg)

    def send_servo(self, pulse: int):
        out = UInt16()
        out.data = max(600, min(2400, pulse))
        self._servo_pub.publish(out)

    def _navsat_callback(self, msg):
        self.gps_fix_updated.emit(msg.status.status)

    def _gps_callback(self, msg):
        lat = msg.pose.position.latitude
        lon = msg.pose.position.longitude
        q = msg.pose.orientation
        # Quaternion (ENU frame) -> yaw -> compass heading (0=North, CW)
        yaw_enu = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                             1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        heading_deg = (90.0 - math.degrees(yaw_enu)) % 360.0
        self.gps_updated.emit(lat, lon, heading_deg)

    def send_command(self, command: str, tab_name: str):
        if not self._command_client.server_is_ready():
            self.command_output.emit(tab_name, '[Error: usv_command_node is not running]\n')
            self.command_done.emit(tab_name, -1)
            return

        if tab_name in self._active_goals:
            self.command_output.emit(tab_name, '[Command already running]\n')
            return

        goal = RunCommand.Goal()
        goal.command = command
        goal.tab_name = tab_name

        future = self._command_client.send_goal_async(
            goal,
            feedback_callback=lambda fb: self.command_output.emit(
                tab_name, fb.feedback.output_line
            ),
        )
        future.add_done_callback(lambda f: self._on_goal_response(tab_name, f))

    def _on_goal_response(self, tab_name: str, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.command_output.emit(tab_name, '[Goal rejected by server]\n')
            self.command_done.emit(tab_name, -1)
            return

        self._active_goals[tab_name] = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(lambda f: self._on_result(tab_name, f))

    def _on_result(self, tab_name: str, future):
        try:
            result = future.result()
            exit_code = result.result.exit_code
        except Exception as e:
            self.get_logger().warn(f'Error getting result for {tab_name}: {e}')
            exit_code = -1
        self._active_goals.pop(tab_name, None)
        self.command_done.emit(tab_name, exit_code)

    def cancel_command(self, tab_name: str):
        goal_handle = self._active_goals.get(tab_name)
        if goal_handle:
            cancel_future = goal_handle.cancel_goal_async()
            cancel_future.add_done_callback(
                lambda f: self._on_cancel_response(tab_name, f)
            )
        else:
            self.get_logger().warn(f'No active goal for tab: {tab_name}')

    def _on_cancel_response(self, tab_name: str, future):
        try:
            response = future.result()
            # clean up manually if the server rejected the cancellation
            if not response.goals_canceling:
                self.get_logger().warn(f'Cancel not accepted for {tab_name}, cleaning up')
                self._active_goals.pop(tab_name, None)
                self.command_done.emit(tab_name, -1)
        except Exception as e:
            self.get_logger().warn(f'Cancel response error for {tab_name}: {e}')
            self._active_goals.pop(tab_name, None)
            self.command_done.emit(tab_name, -1)
