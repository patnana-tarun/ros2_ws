"""
Manual driving that pauses autonomous exploration while it runs.

    ros2 run explorer_exploration manual_drive

While this runs it publishes a heartbeat on /manual_override; explore_coordinator
cancels the current Nav2 goal and waits. Close it (q, Ctrl+C, or close the
terminal) and exploration resumes on its own within about a second.

Velocities go to /cmd_vel_nav - the same input Nav2's controller uses - so they
still pass through the velocity smoother and the collision monitor, which slows
and stops the robot before it hits something. Without Nav2 running (plain
explorer_gazebo.launch.py) use `--ros-args -p topic:=/cmd_vel` instead.
"""

import select
import sys
import termios
import tty

import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from std_msgs.msg import Bool

HELP = """
Manual drive - autonomous exploration is PAUSED while this runs
---------------------------------------------------------------
        w
   a    s    d        w/x : faster / slower (forward, reverse)
        x             a/d : turn left / right faster
                      s or space : stop
q or Ctrl+C : quit and hand back to autonomous exploration
"""


class ManualDrive(Node):
    def __init__(self):
        super().__init__('manual_drive')
        self.declare_parameter('topic', '/cmd_vel_nav')
        self.declare_parameter('max_linear', 0.2)    # m/s, as in nav2_params.yaml
        self.declare_parameter('max_angular', 0.6)   # rad/s
        self.declare_parameter('linear_step', 0.05)
        self.declare_parameter('angular_step', 0.2)
        g = self.get_parameter
        self.max_v, self.max_w = g('max_linear').value, g('max_angular').value
        self.dv, self.dw = g('linear_step').value, g('angular_step').value
        self.cmd_pub = self.create_publisher(TwistStamped, g('topic').value, 10)
        self.override_pub = self.create_publisher(Bool, '/manual_override', 10)
        self.v = self.w = 0.0
        # Keep publishing: the velocity smoother stops the robot if its input goes quiet,
        # and the coordinator resumes exploration if the heartbeat does.
        self.create_timer(0.1, self.publish_cmd)
        self.create_timer(0.2, lambda: self.override_pub.publish(Bool(data=True)))

    def key(self, k):
        if k == 'w':
            self.v = min(self.v + self.dv, self.max_v)
        elif k == 'x':
            self.v = max(self.v - self.dv, -self.max_v)
        elif k == 'a':
            self.w = min(self.w + self.dw, self.max_w)
        elif k == 'd':
            self.w = max(self.w - self.dw, -self.max_w)
        elif k in ('s', ' '):
            self.v = self.w = 0.0
        else:
            return
        print(f'\rlinear {self.v:+.2f} m/s   angular {self.w:+.2f} rad/s   ', end='', flush=True)

    def publish_cmd(self):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_footprint'
        msg.twist.linear.x = self.v
        msg.twist.angular.z = self.w
        self.cmd_pub.publish(msg)

    def release(self):
        """Stop the robot and hand back to exploration straight away."""
        self.v = self.w = 0.0
        for _ in range(3):
            self.publish_cmd()
        self.override_pub.publish(Bool(data=False))


def main(args=None):
    rclpy.init(args=args)
    node = ManualDrive()
    if not sys.stdin.isatty():
        node.get_logger().error('manual_drive needs a terminal (run it with ros2 run, not ros2 launch)')
        return
    settings = termios.tcgetattr(sys.stdin)
    print(HELP)
    try:
        tty.setcbreak(sys.stdin.fileno())
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)
            if select.select([sys.stdin], [], [], 0)[0]:
                k = sys.stdin.read(1)
                if k in ('q', '\x03'):
                    break
                node.key(k)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.release()
        print('\nManual drive closed - autonomous exploration resumes.')
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
