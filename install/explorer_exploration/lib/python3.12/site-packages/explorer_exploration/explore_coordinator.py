"""
Explore coordinator: listens for the best-scoring frontier goal and sends
it to Nav2. Deliberately simple state handling - since frontier_tad_node
recomputes and republishes /best_goal every time the map updates (not just
once), this node just ignores new goals while it's already navigating, and
picks up the latest one once it's free. That avoids needing an explicit
request/trigger protocol between the two nodes.
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus


class ExploreCoordinator(Node):
    def __init__(self):
        super().__init__('explore_coordinator')

        self.goal_sub = self.create_subscription(
            PoseStamped, '/best_goal', self.goal_callback, 10)

        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.busy = False

        self.get_logger().info('Explore coordinator started, waiting for Nav2...')
        self.nav_client.wait_for_server()
        self.get_logger().info('Nav2 action server ready - waiting for goals')

    def goal_callback(self, msg: PoseStamped):
        if self.busy:
            return  # already navigating - ignore updates until this leg finishes

        self.busy = True
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

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def result_callback(self, future):
        status = future.result().status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('Reached goal - ready for next frontier')
        else:
            names = {GoalStatus.STATUS_ABORTED: 'aborted', GoalStatus.STATUS_CANCELED: 'canceled'}
            self.get_logger().warn(
                f'Nav2 gave up on the goal ({names.get(status, status)}) - ready for next frontier')
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
