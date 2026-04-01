#!/usr/bin/env python3
import re
import socket
import threading
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class _RouterOsAPI:
    def __init__(self, host, port=8728, username='admin', password='', timeout=5.0):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)
        self._sock.connect((host, port))
        self._login(username, password)

    def _encode_len(self, n):
        if n < 0x80:
            return bytes([n])
        if n < 0x4000:
            n |= 0x8000
            return bytes([n >> 8, n & 0xFF])
        if n < 0x200000:
            n |= 0xC00000
            return bytes([n >> 16, (n >> 8) & 0xFF, n & 0xFF])
        n |= 0xE0000000
        return bytes([n >> 24, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])

    def _send(self, words):
        buf = b''
        for w in words:
            enc = w.encode()
            buf += self._encode_len(len(enc)) + enc
        buf += b'\x00'
        self._sock.sendall(buf)

    def _recv_len(self):
        b = self._sock.recv(1)
        if not b:
            raise ConnectionError('Connection closed')
        n = b[0]
        if n & 0x80:
            if (n & 0xC0) == 0x80:
                n = ((n & 0x3F) << 8) | self._sock.recv(1)[0]
            elif (n & 0xE0) == 0xC0:
                r = self._sock.recv(2)
                n = ((n & 0x1F) << 16) | (r[0] << 8) | r[1]
            elif (n & 0xF0) == 0xE0:
                r = self._sock.recv(3)
                n = ((n & 0x0F) << 24) | (r[0] << 16) | (r[1] << 8) | r[2]
        return n

    def _recv_sentence(self):
        words = []
        while True:
            n = self._recv_len()
            if n == 0:
                break
            words.append(self._sock.recv(n).decode())
        return words

    def _read_reply(self):
        results = []
        while True:
            sentence = self._recv_sentence()
            if not sentence:
                break
            tag = sentence[0]
            row = {k: v for w in sentence[1:] if w.startswith('=')
                   for k, v in [w[1:].split('=', 1)]}
            if tag == '!done':
                break
            if tag == '!re':
                results.append(row)
            if tag == '!trap':
                raise RuntimeError(row.get('message', 'RouterOS error'))
        return results

    def _login(self, username, password):
        # RouterOS v6.43+ uses single-step plain-text login
        self._send(['/login', f'=name={username}', f'=password={password}'])
        while True:
            sentence = self._recv_sentence()
            if not sentence:
                break
            if sentence[0] == '!done':
                return
            if sentence[0] == '!trap':
                attrs = {k: v for w in sentence[1:] if w.startswith('=')
                         for k, v in [w[1:].split('=', 1)]}
                raise RuntimeError(f"Login failed: {attrs.get('message', 'bad credentials')}")

    def run(self, command, **kwargs):
        words = [command] + [f'={k.replace("_", "-")}={v}' for k, v in kwargs.items()]
        self._send(words)
        return self._read_reply()

    def close(self):
        try:
            self._sock.close()
        except OSError:
            pass


class MikrotikMonitorNode(Node):
    def __init__(self):
        super().__init__('mikrotik_monitor')

        self.declare_parameter('land_ip',       '192.168.2.3')
        self.declare_parameter('boat_ip',       '192.168.2.4')
        self.declare_parameter('api_port',      8728)
        self.declare_parameter('username',      'admin')
        self.declare_parameter('password',      '')
        self.declare_parameter('interface',     'wlan1')
        self.declare_parameter('poll_interval', 2.0)

        self._land_ip  = self.get_parameter('land_ip').value
        self._boat_ip  = self.get_parameter('boat_ip').value
        self._port     = self.get_parameter('api_port').value
        self._user     = self.get_parameter('username').value
        self._password = self.get_parameter('password').value
        self._iface    = self.get_parameter('interface').value
        self._interval = self.get_parameter('poll_interval').value

        # land router: tx = sent to boat, rx = received from boat
        self._land_tx_pub     = self.create_publisher(Float32, 'mikrotik/land/tx_mbps',    10)
        self._land_rx_pub     = self.create_publisher(Float32, 'mikrotik/land/rx_mbps',    10)
        self._land_signal_pub = self.create_publisher(Float32, 'mikrotik/land/signal_dbm', 10)

        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        self.get_logger().info(
            f'MikroTik monitor: land={self._land_ip}, boat={self._boat_ip}, '
            f'iface={self._iface}, poll={self._interval}s'
        )

    def _query(self, host):
        api = _RouterOsAPI(host, self._port, self._user, self._password)
        try:
            # Bandwidth
            bw_rows = api.run('/interface/monitor-traffic', interface=self._iface, once='')
            tx = rx = None
            if bw_rows:
                tx = int(bw_rows[0].get('tx-bits-per-second', 0)) / 1e6
                rx = int(bw_rows[0].get('rx-bits-per-second', 0)) / 1e6

            # Signal strength from wireless registration table
            sig_rows = api.run('/interface/wireless/registration-table/print')
            signal = None
            for row in sig_rows:
                if row.get('interface', '') == self._iface:
                    raw = row.get('signal-strength', '')
                    m = re.search(r'(-?\d+)', raw)
                    if m:
                        signal = float(m.group(1))
                    break

            return tx, rx, signal
        finally:
            api.close()

    def _loop(self):
        while self._running:
            try:
                tx, rx, signal = self._query(self._land_ip)
                if tx is not None:
                    self._land_tx_pub.publish(Float32(data=tx))
                    self._land_rx_pub.publish(Float32(data=rx))
                if signal is not None:
                    self._land_signal_pub.publish(Float32(data=signal))
                self.get_logger().debug(
                    f'Land: to={tx:.2f} from={rx:.2f} Mbps  signal={signal} dBm'
                )
            except Exception as e:
                self.get_logger().warn(f'MikroTik poll failed ({self._land_ip}): {e}')

            time.sleep(self._interval)

    def destroy_node(self):
        self._running = False
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MikrotikMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
