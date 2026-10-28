"""
Bridge to the ESP32 low-level controller (firmware/explorer_esp32) over USB serial.
The ESP32 runs the motors, the 4 wheel encoders and the ICM-20948 IMU; this node gives the
rest of the stack the same topics as the Gazebo simulation.

    ros2 run explorer_bringup esp32_bridge --ros-args -p port:=/dev/ttyUSB0
    ros2 run explorer_bringup esp32_bridge --ros-args -p mock:=true     # no hardware
`port` is a device or any pyserial URL (e.g. socket://host:port).

In:  /cmd_vel (geometry_msgs/TwistStamped) -> 'S,<left>,<right>' side speeds at cmd_rate
Out: /wheel/odom (nav_msgs/Odometry; vx is what the EKF uses), /joint_states (wheel angles),
     /imu (sensor_msgs/Imu, frame imu_link, gyro bias removed, no orientation)

Fusion happens in the robot_localization EKF (explorer_description/config/ekf.yaml):
wheel vx + vy = 0, and the gyro's yaw rate. When the front and rear wheels of a side
disagree (a wheel slipping or in the air), vx is sent with a larger covariance so the EKF
leans on its own prediction instead.

Skid-steer kinematics use an *effective* track width (track_width), not the geometric
0.176 m: the wheels slide sideways when the robot turns. Calibrate it on the robot: command
a turn rate, measure the actual rate (/imu), and scale track_width by commanded/actual.
"""

import math
import random

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState

WHEELS = ['left_front', 'left_middle', 'left_rear', 'right_front', 'right_middle', 'right_rear']
# Telemetry order of the 4 encoders, and which of them each wheel's angle comes from
ENCODED = ['left_front', 'left_rear', 'right_front', 'right_rear']
SOURCE = {'left_front': [0], 'left_middle': [0, 1], 'left_rear': [1],
          'right_front': [2], 'right_middle': [2, 3], 'right_rear': [3]}
IMU_OK, DRIVE_OK, WATCHDOG = 1, 2, 4


def checksum(text):
    c = 0
    for ch in text.encode():
        c ^= ch
    return c


def with_checksum(text):
    return f'{text}*{checksum(text):02X}\n'


class Esp32Bridge(Node):
    def __init__(self):
        super().__init__('esp32_bridge')
        for name, default in [('mock', False), ('port', '/dev/ttyUSB0'), ('baud', 115200),
                              ('wheel_radius', 0.0325), ('track_width', 0.43),
                              ('cmd_timeout', 0.5), ('cmd_rate', 20.0),
                              ('slip_ratio', 0.3), ('imu_frame', 'imu_link'),
                              ('gyro_variance', 4e-6), ('accel_variance', 3e-4)]:
            self.declare_parameter(name, default)
        g = lambda name: self.get_parameter(name).value
        self.mock, self.port, self.baud = g('mock'), g('port'), g('baud')
        self.r, self.track = g('wheel_radius'), g('track_width')
        self.cmd_timeout, self.slip_ratio = g('cmd_timeout'), g('slip_ratio')
        self.imu_frame = g('imu_frame')
        self.gyro_var, self.accel_var = g('gyro_variance'), g('accel_variance')

        self.ser = None
        self.buf = b''
        self.target = (0.0, 0.0)                  # left, right side speed (m/s)
        self.last_cmd = None
        self.prev = None                          # previous T line: (ms, [4 travels in m])
        self.x = self.y = self.th = 0.0
        self.flags = 0
        self.lines = 0                            # valid T lines since the last health check
        self.sim = {'ms': 0, 'travel': [0.0] * 4}  # mock ESP32 state

        self.create_subscription(TwistStamped, 'cmd_vel', self.cmd_cb, 10)
        self.odom_pub = self.create_publisher(Odometry, 'wheel/odom', 10)
        self.js_pub = self.create_publisher(JointState, 'joint_states', 10)
        self.imu_pub = self.create_publisher(Imu, 'imu', 20)
        self.create_timer(1.0 / g('cmd_rate'), self.send_cmd)
        self.create_timer(0.01, self.mock_step if self.mock else self.read_serial)
        self.create_timer(5.0, self.health)
        self.get_logger().info(
            f"esp32_bridge started ({'MOCK - no hardware' if self.mock else self.port}), "
            f'effective track {self.track} m')

    # ---------------- commands -> ESP32
    def cmd_cb(self, msg):
        v, w = msg.twist.linear.x, msg.twist.angular.z
        self.target = (v - w * self.track / 2, v + w * self.track / 2)
        self.last_cmd = self.get_clock().now()

    def send_cmd(self):
        now = self.get_clock().now()
        if self.last_cmd is None or (now - self.last_cmd).nanoseconds / 1e9 > self.cmd_timeout:
            self.target = (0.0, 0.0)
        if self.mock:
            return
        if self.ser is None and not self.open():
            return
        try:
            self.ser.write(with_checksum(f'S,{self.target[0]:.3f},{self.target[1]:.3f}').encode())
        except OSError as e:
            self.lost(e)

    # ---------------- serial
    def open(self):
        import serial
        try:
            # DTR/RTS low: the DevKit's auto-reset circuit leaves the ESP32 running
            ser = serial.serial_for_url(self.port, self.baud, timeout=0, do_not_open=True)
            ser.dtr = ser.rts = False
            ser.open()
        except (serial.SerialException, OSError) as e:
            self.get_logger().warn(f'cannot open {self.port}: {e}', throttle_duration_sec=10.0)
            return False
        self.ser, self.buf, self.prev = ser, b'', None
        self.get_logger().info(f'connected to the ESP32 on {self.port}')
        return True

    def lost(self, err):
        self.get_logger().error(f'ESP32 serial lost ({err}); reconnecting')
        try:
            self.ser.close()
        except OSError:
            pass
        self.ser = None

    def read_serial(self):
        if self.ser is None:
            return
        try:
            self.buf += self.ser.read(4096)
        except OSError as e:
            self.lost(e)
            return
        *lines, self.buf = self.buf.split(b'\n')
        self.buf = self.buf[-512:]                # garbage without newlines (wrong port)
        for raw in lines:
            self.on_line(raw.decode('ascii', errors='replace').strip())

    def on_line(self, line):
        if line.startswith('#'):
            self.get_logger().info(f'ESP32: {line[1:].strip()}')
            return
        body, star, cs = line.partition('*')
        if not star or not body.startswith('T,'):
            return
        try:
            if int(cs, 16) != checksum(body):
                return
            f = body.split(',')
            ms = int(f[1])
            travel = [int(v) * 1e-6 for v in f[2:6]]
            gyro = [float(v) for v in f[6:9]]
            acc = [float(v) for v in f[9:12]]
            self.flags = int(f[14])
        except (ValueError, IndexError):
            return
        self.lines += 1
        self.telemetry(ms, travel, gyro, acc)

    # ---------------- ESP32 telemetry -> ROS
    def telemetry(self, ms, travel, gyro, acc):
        stamp = self.get_clock().now().to_msg()
        if self.flags & IMU_OK:
            self.publish_imu(stamp, gyro, acc)
        if self.prev is None or ms <= self.prev[0]:   # first line, or the ESP32 restarted
            self.prev = (ms, travel)
            return
        dt = (ms - self.prev[0]) / 1000.0
        d = [a - b for a, b in zip(travel, self.prev[1])]
        self.prev = (ms, travel)

        dl, dr = (d[0] + d[1]) / 2, (d[2] + d[3]) / 2
        ds, dth = (dl + dr) / 2, (dr - dl) / self.track
        self.x += ds * math.cos(self.th + dth / 2)
        self.y += ds * math.sin(self.th + dth / 2)
        self.th += dth
        slip = any(abs(a - b) > self.slip_ratio * max(abs(a), abs(b), 0.005 * dt)
                   for a, b in ((d[0], d[1]), (d[2], d[3])))
        self.publish_odom(stamp, ds / dt, dth / dt, slip)

        js = JointState()
        js.header.stamp = stamp
        js.name = [f'{w}_wheel_joint' for w in WHEELS] + ['left_bogie_joint', 'right_bogie_joint']
        js.position = [sum(travel[i] for i in SOURCE[w]) / len(SOURCE[w]) / self.r
                       for w in WHEELS] + [0.0, 0.0]   # bogie angle not sensed
        self.js_pub.publish(js)

    def publish_odom(self, stamp, vx, wz, slip):
        o = Odometry()
        o.header.stamp = stamp
        o.header.frame_id = 'odom'
        o.child_frame_id = 'base_footprint'
        o.pose.pose.position.x, o.pose.pose.position.y = self.x, self.y
        o.pose.pose.orientation.z, o.pose.pose.orientation.w = math.sin(self.th / 2), math.cos(self.th / 2)
        o.twist.twist.linear.x, o.twist.twist.angular.z = vx, wz
        pc = [0.0] * 36
        pc[0] = pc[7] = 0.05
        pc[14] = pc[21] = pc[28] = 1e3
        pc[35] = 0.5
        o.pose.covariance = pc
        # vy = 0 is the skid-steer constraint; wheel yaw rate is poor (the EKF takes the gyro's)
        tc = [0.0] * 36
        tc[0] = 0.25 if slip else 0.002
        tc[7], tc[14], tc[21], tc[28], tc[35] = 0.001, 1e3, 1e3, 1e3, 0.5
        o.twist.covariance = tc
        self.odom_pub.publish(o)

    def publish_imu(self, stamp, gyro, acc):
        m = Imu()
        m.header.stamp = stamp
        m.header.frame_id = self.imu_frame
        m.orientation_covariance[0] = -1.0       # no orientation estimate
        m.angular_velocity.x, m.angular_velocity.y, m.angular_velocity.z = gyro
        m.linear_acceleration.x, m.linear_acceleration.y, m.linear_acceleration.z = acc
        for i in (0, 4, 8):
            m.angular_velocity_covariance[i] = self.gyro_var
            m.linear_acceleration_covariance[i] = self.accel_var
        self.imu_pub.publish(m)

    def health(self):
        if self.mock or self.ser is None:
            return
        if self.lines == 0:
            self.get_logger().warn(f'no telemetry from the ESP32 on {self.port} for 5 s: wrong port '
                                   '(the LiDAR?), firmware not flashed, or still booting')
        elif not self.flags & IMU_OK:
            self.get_logger().warn('ESP32 reports no IMU data: check the ICM-20948 wiring')
        elif not self.flags & DRIVE_OK:
            self.get_logger().warn('ESP32 drive disabled: set TICKS_PER_REV in config.h',
                                   throttle_duration_sec=60.0)
        self.lines = 0

    # ---------------- mock ESP32: follows the targets exactly, IMU chip facing down (URDF)
    def mock_step(self):
        s = self.sim
        s['ms'] += 10
        for i in range(4):
            s['travel'][i] += self.target[0 if i < 2 else 1] * 0.01
        wz = (self.target[1] - self.target[0]) / self.track
        um = [round(t * 1e6) for t in s['travel']]
        noise = lambda: random.gauss(0.0, 0.001)
        # imu_link is rolled 180 deg: robot yaw rate shows as -z, gravity as -9.81 on z
        body = (f"T,{s['ms']},{um[0]},{um[1]},{um[2]},{um[3]},{noise():.5f},{noise():.5f},"
                f'{-wz + noise():.5f},0.000,0.000,-9.807,0,0,{IMU_OK | DRIVE_OK}')
        self.on_line(with_checksum(body).strip())


def main(args=None):
    rclpy.init(args=args)
    node = Esp32Bridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.ser is not None:
            try:
                node.ser.write(with_checksum('S,0,0').encode())
            except OSError:
                pass                              # the ESP32's watchdog stops it anyway
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
