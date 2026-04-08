#!/usr/bin/env python3
import socket
import threading
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32

class SeptentrioNmeaParserNode(Node):
    def __init__(self):
        super().__init__('septentrio_nmea_parser')
        self.declare_parameter('host', '192.168.2.6')
        self.declare_parameter('port', 29001)

        self._rtk_pub   = self.create_publisher(Float32, 'septentrio/rtk_fix',     10)
        self._ntrip_pub = self.create_publisher(Bool,   'septentrio/ntrip_active', 10)
        self._snr_pub   = self.create_publisher(Float32, 'septentrio/snr_avg',     10)
        self._stdlat_pub = self.create_publisher(Float32, 'septentrio/std_lat',    10)
        self._stdlon_pub = self.create_publisher(Float32, 'septentrio/std_lon',    10)

        self._gsv_buf: list[float] = []
        self._gsv_total = 0

        threading.Thread(target=self._tcp_reader, daemon=True).start()
        self.get_logger().info('Septentrio NMEA parser started')

    def _tcp_reader(self):
        host = self.get_parameter('host').value
        port = self.get_parameter('port').value
        while rclpy.ok():
            try:
                self.get_logger().info(f'Connecting to Septentrio at {host}:{port}')
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(5.0)
                    sock.connect((host, port))
                    self.get_logger().info('Connected to Septentrio NMEA stream')
                    buf = ''
                    while rclpy.ok():
                        try:
                            chunk = sock.recv(4096).decode('ascii', errors='ignore')
                            if not chunk:
                                break
                            buf += chunk
                            while '\n' in buf:
                                line, buf = buf.split('\n', 1)
                                self._parse_line(line.strip())
                        except socket.timeout:
                            continue
            except Exception as e:
                self.get_logger().warn(f'Connection error: {e} — retrying in 5 s')
                time.sleep(5.0)

    def _parse_line(self, line: str):
        if not line.startswith('$'):
            return
        if '*' in line:
            line = line[:line.rindex('*')]
        fields = line.split(',')
        sid = fields[0][1:]

        if sid.endswith('GGA'):
            self._parse_gga(fields)
        elif sid.endswith('GST'):
            self._parse_gst(fields)
        elif sid.endswith('GSV'):
            self._parse_gsv(fields)

    def _parse_gga(self, fields):
        try:
            fix = int(fields[6]) if len(fields) > 6 and fields[6] else 0
        except ValueError:
            fix = 0
        msg = Float32()
        msg.data = float(fix)
        self._rtk_pub.publish(msg)
        ntrip = Bool()
        ntrip.data = fix in (4, 5)
        self._ntrip_pub.publish(ntrip)

    def _parse_gst(self, fields):
        # $xxGST,time,rms,smaj,smin,orient,lat_std,lon_std,alt_std
        try:
            if len(fields) > 6 and fields[6]:
                msg = Float32()
                msg.data = float(fields[6])
                self._stdlat_pub.publish(msg)
            if len(fields) > 7 and fields[7]:
                msg = Float32()
                msg.data = float(fields[7])
                self._stdlon_pub.publish(msg)
        except ValueError:
            pass

    def _parse_gsv(self, fields):
        # $xxGSV,total,msg_num,sats,[svid,elev,az,snr]*
        try:
            total   = int(fields[1])
            msg_num = int(fields[2])
        except (ValueError, IndexError):
            return

        if msg_num == 1:
            self._gsv_buf = []
            self._gsv_total = total

        for i in range(4, len(fields), 4):
            snr = fields[i + 3] if i + 3 < len(fields) else ''
            if snr.strip():
                try:
                    self._gsv_buf.append(float(snr))
                except ValueError:
                    pass

        if msg_num == self._gsv_total and self._gsv_buf:
            msg = Float32()
            msg.data = sum(self._gsv_buf) / len(self._gsv_buf)
            self._snr_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(SeptentrioNmeaParserNode())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
