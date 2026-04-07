#!/usr/bin/env python3
import os
import socket
import tempfile
import threading
import time

import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import Bool, UInt16


_SDP = """\
v=0
o=- 0 0 IN IP4 127.0.0.1
s=USV Camera
c=IN IP4 0.0.0.0
t=0 0
m=video {port} RTP/AVP 96
a=rtpmap:96 H264/90000
"""


class UsvPiInterfaceNode(Node):
    def __init__(self):
        super().__init__('usv_pi_interface')

        self.declare_parameter('udp_port',     5600)
        self.declare_parameter('jpeg_quality', 80)
        self.declare_parameter('image_topic',  '/camera/image/compressed')
        self.declare_parameter('pi_ip',        '192.168.2.5')
        self.declare_parameter('servo_port',   5601)
        self.declare_parameter('servo_topic',  '/camera/servo/pulse')

        port              = self.get_parameter('udp_port').value
        self._jpeg_quality = self.get_parameter('jpeg_quality').value
        image_topic       = self.get_parameter('image_topic').value
        self.pi_ip        = self.get_parameter('pi_ip').value
        self.servo_port   = self.get_parameter('servo_port').value
        servo_topic       = self.get_parameter('servo_topic').value

        self.pub = self.create_publisher(CompressedImage, image_topic, 10)

        self._stream_paused = False
        self.servo_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.create_subscription(UInt16, servo_topic, self._servo_callback, 10)
        self.create_subscription(Bool, '/camera/stream/paused', self._paused_callback, 10)

        sdp = tempfile.NamedTemporaryFile(suffix='.sdp', mode='w', delete=False)
        sdp.write(_SDP.format(port=port))
        sdp.flush()
        self._sdp_path = sdp.name

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        self.get_logger().info(f'Listening for H.264 RTP on UDP port {port}')
        self.get_logger().info(f'Publishing to {image_topic}')
        self.get_logger().info(
            f'Servo: {servo_topic} -> UDP {self.pi_ip}:{self.servo_port}'
        )

    def _paused_callback(self, msg):
        self._stream_paused = msg.data
        cmd = b'STREAM_OFF' if msg.data else b'STREAM_ON'
        try:
            self.servo_sock.sendto(cmd, (self.pi_ip, self.servo_port))
        except Exception as e:
            self.get_logger().warn(f'Stream control UDP send failed: {e}')

    def _servo_callback(self, msg):
        pulse = max(600, min(2400, int(msg.data)))
        try:
            self.servo_sock.sendto(str(pulse).encode(), (self.pi_ip, self.servo_port))
        except Exception as e:
            self.get_logger().warn(f'Servo UDP send failed: {e}')

    def _loop(self):
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality]
        frame_count = 0
        last_log = time.time()

        while self._running:
            if self._stream_paused:
                time.sleep(0.5)
                continue

            self.get_logger().info('Opening stream...')
            os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = (
                'protocol_whitelist;file,rtp,udp,crypto,data'
                '|fflags;nobuffer'
                '|max_delay;0'
                '|reorder_queue_size;0'
            )
            cap = cv2.VideoCapture(self._sdp_path, cv2.CAP_FFMPEG)

            if not cap.isOpened():
                self.get_logger().error('Failed to open stream, retrying in 3s...')
                time.sleep(3)
                continue

            self.get_logger().info('Stream opened.')

            while self._running and not self._stream_paused:
                ret, frame = cap.read()
                if not ret:
                    break

                ok, jpeg_buf = cv2.imencode('.jpg', frame, encode_params)
                if not ok:
                    continue

                msg = CompressedImage()
                msg.header.stamp    = self.get_clock().now().to_msg()
                msg.header.frame_id = 'camera'
                msg.format = 'jpeg'
                msg.data   = jpeg_buf.tobytes()
                self.pub.publish(msg)

                frame_count += 1
                now = time.time()
                if now - last_log >= 5.0:
                    self.get_logger().info(f'{frame_count / (now - last_log):.1f} fps')
                    frame_count = 0
                    last_log = now

            cap.release()
            if self._running and not self._stream_paused:
                self.get_logger().warn('Stream ended, reconnecting in 3s...')
                time.sleep(3)

    def destroy_node(self):
        self._running = False
        try:
            os.unlink(self._sdp_path)
        except OSError:
            pass
        self.servo_sock.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = UsvPiInterfaceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
