"""
Drive-mode switcher: reverse allowed inside tunnels, forward driving in open space.

The navigate-to-pose BT has a ControllerSelector that reads the controller name from
/controller_selector. This node measures how wide the passage is from the LiDAR (left + right
clearance at +-90 deg) and publishes:
  - reverse_controller (e.g. FollowPathReverse: MPPI may follow the path backwards) while the
    robot is in a tunnel, so it backs out of dead ends instead of turning round in them
  - forward_controller (FollowPath: forward preferred) in open space, so a robot that backed
    out of a tunnel turns round there and explores forward instead of carrying on backwards
(user's request, 2026-10-20)

Hysteresis: tunnel when width < tunnel_width, open when width > open_width, and a change needs
dwell_s seconds of consistent readings, so the mode doesn't flicker at tunnel mouths.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String


class DriveModeSwitcher(Node):
    def __init__(self):
        super().__init__('drive_mode_switcher')
        self.declare_parameter('tunnel_width', 1.2)
        self.declare_parameter('open_width', 1.8)
        self.declare_parameter('dwell_s', 1.0)
        self.declare_parameter('side_window_deg', 10.0)
        self.declare_parameter('forward_controller', 'FollowPath')
        self.declare_parameter('reverse_controller', 'FollowPathReverse')
        g = lambda n: self.get_parameter(n).value
        self.tunnel_w, self.open_w, self.dwell = g('tunnel_width'), g('open_width'), g('dwell_s')
        self.win = math.radians(g('side_window_deg'))
        self.ctrl = {'open': g('forward_controller'), 'tunnel': g('reverse_controller')}

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
        self.pub = self.create_publisher(String, '/controller_selector', latched)
        self.mode = 'open'
        self.candidate, self.since = None, None
        self.publish()
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.get_logger().info(
            f'Drive mode switcher: tunnel < {self.tunnel_w} m -> {self.ctrl["tunnel"]}, '
            f'open > {self.open_w} m -> {self.ctrl["open"]}, dwell {self.dwell} s')

    def publish(self):
        self.pub.publish(String(data=self.ctrl[self.mode]))

    def side(self, msg, centre):
        best = math.inf
        for i, r in enumerate(msg.ranges):
            a = msg.angle_min + i * msg.angle_increment
            d = math.atan2(math.sin(a - centre), math.cos(a - centre))
            if abs(d) < self.win and msg.range_min < r < msg.range_max:
                best = min(best, r)
        return best if best < math.inf else msg.range_max

    def on_scan(self, msg):
        width = self.side(msg, math.pi / 2) + self.side(msg, -math.pi / 2)
        want = 'tunnel' if width < self.tunnel_w else 'open' if width > self.open_w else self.mode
        now = self.get_clock().now().nanoseconds / 1e9
        if want == self.mode:
            self.candidate, self.since = None, None
            return
        if want != self.candidate:
            self.candidate, self.since = want, now
            return
        if now - self.since >= self.dwell:
            self.mode = want
            self.candidate, self.since = None, None
            self.publish()
            self.get_logger().info(f'{self.mode} (width {width:.2f} m) -> {self.ctrl[self.mode]}')


def main(args=None):
    rclpy.init(args=args)
    node = DriveModeSwitcher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
