#!/usr/bin/env python3
import subprocess
import threading
import yaml
import os

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from ament_index_python.packages import get_package_share_directory


class UsvExternalPinger(Node):
    def __init__(self):
        super().__init__('usv_external_pinger')

        config_path = os.path.join(
            get_package_share_directory('usv_diagnostic_gui'),
            'config', 'config.yaml'
        )
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self._use_host_exec = subprocess.run(
            ['which', 'distrobox-host-exec'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode == 0
        if self._use_host_exec:
            self.get_logger().info('Distrobox detected: using distrobox-host-exec for ping')

        hosts = config.get('pinger_hosts', [])
        if not hosts:
            self.get_logger().warn('No pinger_hosts found in config.yaml')

        self._pinger_pubs = {}
        for host in hosts:
            topic = host['topic']
            ip = host['ip']
            label = host.get('label', topic)
            pub = self.create_publisher(Bool, topic, 10)
            self._pinger_pubs[topic] = {'pub': pub, 'ip': ip, 'label': label}
            self.get_logger().info(f'Pinger: {label} ({ip}) -> {topic}')

        self.create_timer(1.0, self._ping_all)

    def _ping(self, ip: str) -> bool:
        try:
            cmd = (
                ['distrobox-host-exec', 'ping', '-c', '1', '-W', '1', ip]
                if self._use_host_exec
                else ['ping', '-c', '1', '-W', '1', ip]
            )
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return result.returncode == 0
        except Exception as e:
            self.get_logger().error(f'ping error for {ip}: {e}')
            return False

    def _ping_one(self, topic, entry):
        reachable = self._ping(entry['ip'])
        msg = Bool()
        msg.data = reachable
        entry['pub'].publish(msg)
        if not reachable:
            self.get_logger().warn(f"{entry['label']} ({entry['ip']}): DOWN")

    def _ping_all(self):
        threads = [
            threading.Thread(target=self._ping_one, args=(topic, entry), daemon=True)
            for topic, entry in self._pinger_pubs.items()
        ]
        for t in threads:
            t.start()


def main(args=None):
    rclpy.init(args=args)
    node = UsvExternalPinger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
