"""
Explore coordinator: listens for the best-scoring frontier goal and sends
it to Nav2. Deliberately simple state handling - since frontier_tad_node
recomputes and republishes /best_goal every time the map updates (not just
once), this node just ignores new goals while it's already navigating, and
picks up the latest one once it's free. That avoids needing an explicit
request/trigger protocol between the two nodes.

Goal timeout: a goal is abandoned after max(goal_timeout_min, goal_timeout_per_m x
straight-line distance) seconds. Aborted or timed-out goals are published on
/frontier_blacklist so frontier_tad_node stops choosing that frontier for a while
(otherwise one unreachable frontier among rocks kept the robot busy for 9 minutes).

Manual override: while `manual_drive` runs it publishes a heartbeat on
/manual_override. On the first heartbeat this node cancels the current Nav2
goal and stops sending goals; when heartbeats stop for override_timeout
seconds (terminal closed, Ctrl+C, crash) it resumes with the next /best_goal.
"""

import math

import rclpy
import tf2_ros
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PointStamped, PoseStamped
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus
from std_msgs.msg import Bool


class ExploreCoordinator(Node):
    def __init__(self):
        super().__init__('explore_coordinator')

        self.goal_sub = self.create_subscription(
            PoseStamped, '/best_goal', self.goal_callback, 10)

        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.busy = False
        self.goal_handle = None

        self.declare_parameter('goal_timeout_min', 60.0)
        self.declare_parameter('goal_timeout_per_m', 15.0)
        self.t_min = self.get_parameter('goal_timeout_min').value
        self.t_per_m = self.get_parameter('goal_timeout_per_m').value
        self.goal = None            # PoseStamped currently being navigated to
        self.deadline = None
        self.robot_xy = None
        self.blacklist_pub = self.create_publisher(PointStamped, '/frontier_blacklist', 10)
        self.timed_out = False
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.create_timer(1.0, self.check_timeout)

        self.declare_parameter('override_timeout', 1.0)
        self.override_timeout = self.get_parameter('override_timeout').value
        self.last_heartbeat = None   # time of the last /manual_override True
        self.paused = False
        self.create_subscription(Bool, '/manual_override', self.override_callback, 10)
        self.create_timer(0.2, self.check_override)

        self.get_logger().info('Explore coordinator started, waiting for Nav2...')
        self.nav_client.wait_for_server()
        self.get_logger().info('Nav2 action server ready - waiting for goals')

    def override_callback(self, msg: Bool):
        if msg.data:
            self.last_heartbeat = self.get_clock().now()
        else:
            self.last_heartbeat = None      # manual_drive said goodbye: resume now
        self.check_override()

    def check_override(self):
        now = self.get_clock().now()
        active = (self.last_heartbeat is not None and
                  (now - self.last_heartbeat).nanoseconds / 1e9 < self.override_timeout)
        if active and not self.paused:
            self.paused = True
            self.get_logger().info('Manual override - exploration paused')
            if self.goal_handle is not None:
                self.goal_handle.cancel_goal_async()
        elif not active and self.paused:
            self.paused = False
            self.get_logger().info('Manual override ended - resuming exploration')

    def distance_to(self, goal):
        """Straight-line robot->goal distance from TF (0 if unknown)."""
        try:
            t = self.tf_buffer.lookup_transform('map', 'base_footprint', rclpy.time.Time())
            return math.hypot(goal.pose.position.x - t.transform.translation.x,
                              goal.pose.position.y - t.transform.translation.y)
        except Exception:
            return 0.0

    def check_timeout(self):
        if self.deadline is None or self.goal_handle is None:
            return
        if self.get_clock().now().nanoseconds / 1e9 > self.deadline:
            self.get_logger().warn('Goal took too long - cancelling it')
            self.timed_out = True
            self.deadline = None
            self.goal_handle.cancel_goal_async()

    def goal_callback(self, msg: PoseStamped):
        if self.paused:
            return  # manual driving - no autonomous goals
        if self.busy:
            return  # already navigating - ignore updates until this leg finishes

        self.busy = True
        self.goal = msg
        self.timed_out = False
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = msg

        self.get_logger().info(
            f'Sending goal: ({msg.pose.position.x:.2f}, {msg.pose.position.y:.2f})')

        send_goal_future = self.nav_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Goal rejected by Nav2')
            self.busy = False
            return

        self.goal_handle = goal_handle
        dist = self.distance_to(self.goal)
        self.deadline = self.get_clock().now().nanoseconds / 1e9 + max(self.t_min, self.t_per_m * dist)
        if self.paused:                 # override began while the goal was in flight
            goal_handle.cancel_goal_async()
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def result_callback(self, future):
        status = future.result().status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('Reached goal - ready for next frontier')
        else:
            names = {GoalStatus.STATUS_ABORTED: 'aborted', GoalStatus.STATUS_CANCELED: 'canceled'}
            reason = 'timed out' if self.timed_out else names.get(status, status)
            self.get_logger().warn(f'Nav2 gave up on the goal ({reason}) - ready for next frontier')
            # A manual-override cancel is not the frontier's fault; anything else is.
            if (status == GoalStatus.STATUS_ABORTED or self.timed_out) and self.goal is not None:
                bl = PointStamped()
                bl.header = self.goal.header
                bl.point.x, bl.point.y = self.goal.pose.position.x, self.goal.pose.position.y
                self.blacklist_pub.publish(bl)
        self.goal_handle = None
        self.deadline = None
        self.busy = False


def main(args=None):
    rclpy.init(args=args)
    node = ExploreCoordinator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
