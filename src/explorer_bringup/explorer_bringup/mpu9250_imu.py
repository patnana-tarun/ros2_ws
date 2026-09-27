"""
MPU-9250 IMU driver (gyro + accelerometer over I2C) for the real explorer robot.

    ros2 run explorer_bringup mpu9250_imu
    ros2 run explorer_bringup mpu9250_imu --ros-args -p mock:=true     # no hardware

Out: /imu (sensor_msgs/Imu), frame imu_link. The chip is mounted under the base plate,
facing down, +x to the left, +z down (user, 2026-09-26); the URDF's imu_joint describes
that, so the data is published in the chip's own axes and robot_localization rotates it.

- Keep the robot still for the first calibration_s seconds: the gyro bias is measured then.
- Orientation is not estimated (orientation_covariance[0] = -1). The EKF only uses yaw
  rate. The magnetometer (AK8963) is not read.
- Needs I2C enabled on the Pi and smbus2 (sudo apt install python3-smbus2).
"""

import math
import struct

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

PWR_MGMT_1, SMPLRT_DIV, CONFIG, GYRO_CONFIG, ACCEL_CONFIG, ACCEL_XOUT_H, WHO_AM_I = \
    0x6B, 0x19, 0x1A, 0x1B, 0x1C, 0x3B, 0x75
GYRO_LSB = 131.0        # LSB per deg/s at +/-250 deg/s
ACCEL_LSB = 16384.0     # LSB per g at +/-2 g
G = 9.80665


def parse(block):
    """14 bytes from ACCEL_XOUT_H -> (accel m/s^2, gyro rad/s) in chip axes."""
    ax, ay, az, _temp, gx, gy, gz = struct.unpack('>7h', bytes(block))
    accel = [v / ACCEL_LSB * G for v in (ax, ay, az)]
    gyro = [math.radians(v / GYRO_LSB) for v in (gx, gy, gz)]
    return accel, gyro


class Mpu9250(Node):
    def __init__(self):
        super().__init__('mpu9250_imu')
        self.declare_parameter('mock', False)
        self.declare_parameter('bus', 1)
        self.declare_parameter('address', 0x68)
        self.declare_parameter('rate', 100.0)
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('calibration_s', 2.0)
        g = lambda n: self.get_parameter(n).value
        self.mock, self.addr, self.frame = g('mock'), g('address'), g('frame_id')
        self.bus = None
        if not self.mock:
            from smbus2 import SMBus
            self.bus = SMBus(g('bus'))
            who = self.bus.read_byte_data(self.addr, WHO_AM_I)
            if who not in (0x71, 0x73, 0x70):   # MPU-9250, MPU-9255, MPU-6500 core
                self.get_logger().warn(f'WHO_AM_I = 0x{who:02x}, expected 0x71 (MPU-9250)')
            self.bus.write_byte_data(self.addr, PWR_MGMT_1, 0x01)    # wake, PLL clock
            self.bus.write_byte_data(self.addr, CONFIG, 0x03)        # DLPF 41 Hz
            self.bus.write_byte_data(self.addr, SMPLRT_DIV, 0x09)    # 1 kHz / 10 = 100 Hz
            self.bus.write_byte_data(self.addr, GYRO_CONFIG, 0x00)   # +/-250 deg/s
            self.bus.write_byte_data(self.addr, ACCEL_CONFIG, 0x00)  # +/-2 g
        self.calib_n = int(g('calibration_s') * g('rate'))
        self.calib = []
        self.bias = [0.0, 0.0, 0.0]
        self.pub = self.create_publisher(Imu, 'imu', 20)
        self.create_timer(1.0 / g('rate'), self.update)
        self.get_logger().info(f"mpu9250_imu started ({'MOCK' if self.mock else 'I2C'}); "
                               f"keep the robot still for {g('calibration_s')} s")

    def read(self):
        if self.mock:   # still robot, chip facing down: gravity on -z of the chip
            return [0.0, 0.0, -G], [0.001, -0.002, 0.0015]
        return parse(self.bus.read_i2c_block_data(self.addr, ACCEL_XOUT_H, 14))

    def update(self):
        try:
            accel, gyro = self.read()
        except OSError as e:    # I2C glitch: skip this sample
            self.get_logger().warn(f'I2C read failed: {e}', throttle_duration_sec=5.0)
            return
        if len(self.calib) < self.calib_n:
            self.calib.append(gyro)
            if len(self.calib) == self.calib_n:
                self.bias = [sum(c[i] for c in self.calib) / self.calib_n for i in range(3)]
                self.get_logger().info('gyro bias (rad/s): ' + ', '.join(f'{b:+.4f}' for b in self.bias))
            return
        m = Imu()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = self.frame
        m.orientation_covariance[0] = -1.0
        (m.angular_velocity.x, m.angular_velocity.y, m.angular_velocity.z) = \
            [w - b for w, b in zip(gyro, self.bias)]
        (m.linear_acceleration.x, m.linear_acceleration.y, m.linear_acceleration.z) = accel
        m.angular_velocity_covariance[0] = m.angular_velocity_covariance[4] = \
            m.angular_velocity_covariance[8] = 1.5e-6     # (0.0012 rad/s)^2, datasheet noise
        m.linear_acceleration_covariance[0] = m.linear_acceleration_covariance[4] = \
            m.linear_acceleration_covariance[8] = 4.5e-4  # (0.021 m/s^2)^2
        self.pub.publish(m)


def main(args=None):
    rclpy.init(args=args)
    node = Mpu9250()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
