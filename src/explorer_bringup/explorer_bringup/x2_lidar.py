"""
YDLIDAR X2 driver (pure Python, no YDLidar-SDK): serial packets -> sensor_msgs/LaserScan.

    ros2 run explorer_bringup x2_lidar --ros-args -p port:=/dev/ttyUSB1

The X2 needs no commands: powered, it spins and streams packets at 115200 baud.
    AA 55 | CT | LSN | FSA (2) | LSA (2) | CS (2) | LSN x Si (2)       little-endian
    CT bit 0 = 1 marks the first packet of a turn; angle = (FSA or LSA >> 1) / 64 deg,
    spread evenly over the LSN samples; distance = Si / 4 mm, plus the X2's
    triangulation angle correction; CS = XOR of all 16-bit words except itself.
Each turn becomes one scan of `beams` fixed bins (nearest point per bin), so every scan has
the same size for SLAM Toolbox. The X2 turns clockwise; `inverted` makes the angles
counter-clockwise, as ROS expects. `angle_offset_deg` turns the scan so 0 = robot forward:
check it once with an object in front of the robot (RViz, /scan in laser_frame).
`port` is a device or any pyserial URL (e.g. socket://host:port).
"""

import math
import struct

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

HEADER = b'\xaa\x55'


def parse(buf):
    """Return ([(start_of_turn, [(angle_deg, dist_mm), ...]), ...], unparsed rest of buf)."""
    packets = []
    while True:
        i = buf.find(HEADER)
        if i < 0:
            return packets, buf[-1:]
        buf = buf[i:]
        if len(buf) < 10:
            return packets, buf
        ct, lsn, fsa, lsa, cs = struct.unpack_from('<BBHHH', buf, 2)
        size = 10 + 2 * lsn
        if len(buf) < size:
            return packets, buf
        samples = struct.unpack_from(f'<{lsn}H', buf, 10)
        check = 0x55AA ^ (lsn << 8 | ct) ^ fsa ^ lsa
        for s in samples:
            check ^= s
        if check != cs or lsn == 0:
            buf = buf[2:]                         # not a real header: resync
            continue
        buf = buf[size:]
        start, end = (fsa >> 1) / 64.0, (lsa >> 1) / 64.0
        span = (end - start) % 360.0
        points = []
        for k, s in enumerate(samples):
            dist = s / 4.0
            angle = start + (span * k / (lsn - 1) if lsn > 1 else 0.0)
            if dist > 0:
                angle += math.degrees(math.atan(21.8 * (155.3 - dist) / (155.3 * dist)))
            points.append((angle, dist))
        packets.append((bool(ct & 1), points))


class X2Lidar(Node):
    def __init__(self):
        super().__init__('x2_lidar')
        for name, default in [('port', '/dev/ttyUSB1'), ('baud', 115200),
                              ('frame_id', 'laser_frame'), ('beams', 360),
                              ('range_min', 0.12), ('range_max', 8.0),
                              ('inverted', True), ('angle_offset_deg', 0.0),
                              ('motor_dtr', True)]:
            self.declare_parameter(name, default)
        g = lambda name: self.get_parameter(name).value
        self.port, self.baud, self.frame = g('port'), g('baud'), g('frame_id')
        self.beams, self.rmin, self.rmax = g('beams'), g('range_min'), g('range_max')
        self.sign = -1.0 if g('inverted') else 1.0
        self.offset, self.motor_dtr = g('angle_offset_deg'), g('motor_dtr')

        self.ser = None
        self.buf = b''
        self.points = []
        self.turn_start = None                    # ROS time of the current turn's start
        self.scans = 0
        self.pub = self.create_publisher(LaserScan, 'scan', 10)
        self.create_timer(0.005, self.read)
        self.create_timer(5.0, self.health)
        self.get_logger().info(f'x2_lidar started on {self.port}, {self.beams} beams')

    def open(self):
        import serial
        try:
            self.ser = serial.serial_for_url(self.port, self.baud, timeout=0)
        except (serial.SerialException, OSError) as e:
            self.get_logger().warn(f'cannot open {self.port}: {e}', throttle_duration_sec=10.0)
            return
        try:
            self.ser.dtr = self.motor_dtr         # the X2 adapter's DTR switches the motor
        except OSError as e:
            self.get_logger().warn(f'cannot set DTR on {self.port} ({e}); motor left as it is')

    def read(self):
        if self.ser is None:
            self.open()
            return
        try:
            self.buf += self.ser.read(4096)
        except OSError as e:
            self.get_logger().error(f'LiDAR serial lost ({e}); reconnecting')
            self.ser.close()
            self.ser = None
            return
        packets, self.buf = parse(self.buf)
        for start, points in packets:
            if start:
                self.new_turn()
            self.points += points

    def new_turn(self):
        now = self.get_clock().now()
        if self.turn_start is not None and len(self.points) > self.beams // 4:
            self.publish(self.turn_start, (now - self.turn_start).nanoseconds / 1e9)
        self.turn_start, self.points = now, []

    def publish(self, start, scan_time):
        inc = 2 * math.pi / self.beams
        ranges = [math.inf] * self.beams
        for angle, dist in self.points:
            r = dist / 1000.0
            if not self.rmin <= r <= self.rmax:
                continue
            a = math.radians(self.sign * angle + self.offset)
            k = int((a + math.pi) % (2 * math.pi) / inc) % self.beams
            ranges[k] = min(ranges[k], r)
        m = LaserScan()
        m.header.stamp = start.to_msg()
        m.header.frame_id = self.frame
        m.angle_min, m.angle_increment = -math.pi, inc
        m.angle_max = -math.pi + inc * (self.beams - 1)
        m.scan_time, m.time_increment = scan_time, scan_time / self.beams
        m.range_min, m.range_max = self.rmin, self.rmax
        m.ranges = ranges
        self.pub.publish(m)
        self.scans += 1

    def health(self):
        if self.ser is not None and self.scans == 0:
            self.get_logger().warn(f'no scans from {self.port} for 5 s: wrong port (the ESP32?), '
                                   'or the motor is off (try motor_dtr:=false)')
        self.scans = 0

    def stop(self):
        if self.ser is not None:
            try:
                self.ser.dtr = not self.motor_dtr
            except OSError:
                pass
            self.ser.close()


def main(args=None):
    rclpy.init(args=args)
    node = X2Lidar()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
