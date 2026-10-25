"""
Demo view box: keeps the RViz map view still while the robot drives inside an imaginary box, and
recentres it on the robot once the robot leaves the box (user's request, 2026-10-24, for the
review demo recording).

Publishes TF global_frame -> anchor_frame (view_anchor). The demo RViz config
(rviz/demo_view.rviz) uses view_anchor as the TopDownOrtho Target Frame, so the view is centred
on the anchor. The anchor sits still while the robot is inside the box_x by box_y box around it;
when the robot crosses the box edge, the anchor glides (smoothstep, glide_s seconds) to where the
robot was at that moment, and the box is drawn there again. The box outline goes to
/demo/view_box (Marker) so the audience can see it; show_box:=false hides it.

Only follows TF, so it works the same under autonomous exploration and manual_drive.

    ros2 run explorer_exploration demo_view_box --ros-args -p use_sim_time:=true
    ros2 run explorer_exploration demo_view_box --ros-args -p use_sim_time:=true -p box_x:=6.0
"""

import time

import rclpy
from geometry_msgs.msg import Point, TransformStamped
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformBroadcaster, TransformListener
from visualization_msgs.msg import Marker


class DemoViewBox(Node):
    def __init__(self):
        super().__init__('demo_view_box')
        self.declare_parameter('box_x', 4.0)            # box size along map x (m)
        self.declare_parameter('box_y', 4.0)            # box size along map y (m)
        self.declare_parameter('glide_s', 1.0)          # recentre time (s); 0 = snap
        self.declare_parameter('rate', 30.0)            # TF publish rate (Hz)
        self.declare_parameter('global_frame', 'map')
        self.declare_parameter('robot_frame', 'base_footprint')
        self.declare_parameter('anchor_frame', 'view_anchor')
        self.declare_parameter('show_box', True)
        g = lambda n: self.get_parameter(n).value
        self.half_x, self.half_y = g('box_x') / 2.0, g('box_y') / 2.0
        self.glide_s = g('glide_s')
        self.global_frame, self.robot_frame = g('global_frame'), g('robot_frame')
        self.anchor_frame, self.show_box = g('anchor_frame'), g('show_box')

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tf_pub = TransformBroadcaster(self)
        self.box_pub = self.create_publisher(Marker, '/demo/view_box', 1)

        self.center = None          # anchor position now (x, y)
        self.glide = None           # (start_xy, goal_xy, t0 in monotonic seconds)
        self.create_timer(1.0 / g('rate'), self.tick)
        self.get_logger().info(f'view box {2 * self.half_x:.1f} x {2 * self.half_y:.1f} m, '
                               f'glide {self.glide_s:.1f} s, anchor {self.anchor_frame}')

    def robot_xy(self):
        try:
            t = self.tf_buffer.lookup_transform(self.global_frame, self.robot_frame, Time())
        except Exception:
            return None
        return t.transform.translation.x, t.transform.translation.y

    def tick(self):
        robot = self.robot_xy()
        if robot is None:
            return
        # wall time for the glide: it is a screen effect, it should look the same at any RTF
        now_s = time.monotonic()
        if self.center is None:
            self.center = robot
        if self.glide is not None:
            (x0, y0), (x1, y1), t0 = self.glide
            u = 1.0 if self.glide_s <= 0 else min(1.0, (now_s - t0) / self.glide_s)
            u = u * u * (3.0 - 2.0 * u)
            self.center = (x0 + (x1 - x0) * u, y0 + (y1 - y0) * u)
            if u >= 1.0:
                self.glide = None
        elif abs(robot[0] - self.center[0]) > self.half_x or abs(robot[1] - self.center[1]) > self.half_y:
            self.glide = (self.center, robot, now_s)
            self.get_logger().info(f'robot left the box: recentre on ({robot[0]:.1f}, {robot[1]:.1f})')
        self.publish(self.center)

    def publish(self, c):
        stamp = self.get_clock().now().to_msg()
        t = TransformStamped()
        t.header.stamp = stamp
        t.header.frame_id = self.global_frame
        t.child_frame_id = self.anchor_frame
        t.transform.translation.x, t.transform.translation.y = c
        t.transform.rotation.w = 1.0
        self.tf_pub.sendTransform(t)
        if not self.show_box:
            return
        m = Marker()
        m.header.stamp = stamp
        m.header.frame_id = self.global_frame
        m.ns, m.id = 'view_box', 0
        m.type, m.action = Marker.LINE_STRIP, Marker.ADD
        m.pose.orientation.w = 1.0
        m.scale.x = 0.05
        m.color.r, m.color.g, m.color.b, m.color.a = 1.0, 0.8, 0.0, 0.9
        hx, hy = self.half_x, self.half_y
        m.points = [Point(x=c[0] + sx * hx, y=c[1] + sy * hy, z=0.05)
                    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))]
        self.box_pub.publish(m)


def main():
    rclpy.init()
    node = DemoViewBox()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
