"""
Instrumentation for comparing our exploration run against the TAD paper's
reported metrics (Buriboev, Choi & Jeon 2025, Figures 12-14 / Table 5):
exploration time, path distance, and goal (turning-point) count.

- Path distance: summed from consecutive /odom positions. Odometry
  integrates actual wheel motion, so this is the ground-truth distance
  the robot physically travelled - the same quantity the paper measures.
- Goal count: incremented each time /best_goal changes to a new position.
  This is our stand-in for the paper's "turning points" - the paper
  counts heading-change events along the executed path, which needs
  path-follower internals we don't have visibility into; goal count is
  the coarser, comparable proxy (number of distinct target selections).
- Exploration time: wall/sim-clock delta between the first /odom message
  and the first /exploration_complete message.
- Coverage: fraction of non-unknown cells in the final /map.

Prints one summary line on completion and keeps running (a second
/exploration_complete is ignored) so it can be tailed in a log file by an
external benchmark script.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from nav_msgs.msg import Odometry, OccupancyGrid
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Empty


class MetricsLogger(Node):
    def __init__(self):
        super().__init__('metrics_logger')

        self.start_time = None
        self.last_xy = None
        self.path_distance = 0.0
        self.goal_count = 0
        self.last_goal_xy = None
        self.last_map = None
        self.done = False

        self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.create_subscription(PoseStamped, '/best_goal', self.goal_cb, 10)
        self.create_subscription(Empty, '/exploration_complete', self.complete_cb, 10)

        map_qos = QoSProfile(depth=1)
        map_qos.reliability = ReliabilityPolicy.RELIABLE
        map_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(OccupancyGrid, '/map', self.map_cb, map_qos)

        self.get_logger().info('Metrics logger started')

    def odom_cb(self, msg: Odometry):
        if self.done:
            return
        if self.start_time is None:
            self.start_time = self.get_clock().now()
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        if self.last_xy is not None:
            self.path_distance += math.hypot(x - self.last_xy[0], y - self.last_xy[1])
        self.last_xy = (x, y)

    def goal_cb(self, msg: PoseStamped):
        if self.done:
            return
        x, y = msg.pose.position.x, msg.pose.position.y
        if self.last_goal_xy is None or math.hypot(x - self.last_goal_xy[0], y - self.last_goal_xy[1]) > 1e-3:
            self.goal_count += 1
            self.last_goal_xy = (x, y)

    def map_cb(self, msg: OccupancyGrid):
        self.last_map = msg

    def complete_cb(self, msg: Empty):
        if self.done or self.start_time is None:
            return
        self.done = True
        elapsed = (self.get_clock().now() - self.start_time).nanoseconds / 1e9

        coverage = float('nan')
        if self.last_map is not None:
            data = self.last_map.data
            known = sum(1 for c in data if c != -1)
            coverage = 100.0 * known / len(data) if data else float('nan')

        self.get_logger().info(
            'METRICS_SUMMARY '
            f'exploration_time_s={elapsed:.1f} '
            f'path_distance_m={self.path_distance:.2f} '
            f'goal_count={self.goal_count} '
            f'coverage_pct={coverage:.1f}'
        )


def main(args=None):
    rclpy.init(args=args)
    node = MetricsLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
