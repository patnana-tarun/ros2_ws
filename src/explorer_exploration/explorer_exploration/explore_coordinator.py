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

Stall give-up (stall_timeout, 0 = off): a goal is also abandoned and blacklisted when the robot's
net movement over the last stall_timeout seconds is below stall_radius. With 30 s / 0.3 m this
is two of Nav2's progress-checker windows (0.3 m in 15 s), so a frontier the robot can't make
progress toward costs about 30 s instead of the 60 s minimum timeout (measured 2026-10-18:
median 60 s per failed goal, 56 of 58 failures ended by the timeout).

Path pre-check (precheck_path, off by default): before sending a frontier to Nav2, ask the
planner once for a path to it. If there is none, blacklist the frontier at once instead of
letting the navigator's recovery tree (clear, BackUp, Spin, Wait, up to 6 rounds) work on a
goal the planner already refuses. Smac Lattice refuses goals the real footprint cannot reach
(docs/issues/Planner comparison 2026-10-18.md).

Retrace (retrace_distance, 0 = off; user's idea, 2026-10-20): when the robot gets stuck in a tight
passage, it backs out along its own recorded track (known to be free: it just drove it) instead
of waiting for a controller that may stand still there. Triggered by a stall give-up in which the
robot moved less than retrace_max_moved (really stuck, not creeping: 2026-10-20 a run backed out
of every slow squeeze and undid its own progress for 36 min), or by retrace_after_fails failed
goals in a row without the robot moving 0.5 m. Loop guard (stall trigger only): no second
retrace starting within 0.5 m of the last one for 300 s. Failed goals at one spot are about the
robot's position, so they may retrace again there (a run sat 4 min with the guard blocking it).

Pre-check failures clear the global costmap before the frontier's second check, like Nav2's own
recovery does: a stale obstacle near the robot otherwise fails every frontier in turn. With
retrace_controller set (e.g. FollowPathReverse) it only runs while /controller_selector names
that controller, i.e. in tunnels. Commands go to /cmd_vel_nav like manual_drive, so the velocity
smoother and the collision monitor still apply. It stops after retrace_distance along the
track, or when blocked (no movement for 6 s), or after retrace_timeout.

Explored goals (explored_cancel, off by default): the frontier node republishes its candidate frontiers
(/frontier_markers) on every map update. When no candidate has been within 1 m of the current goal
for two updates in a row, the LiDAR has already explored it: the goal is cancelled (not blacklisted)
and the next frontier is taken from where the robot is, instead of driving into the pocket and turning
round. Frontier goals are often LiDAR shadows behind boulders that disappear on the way there.

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
from geometry_msgs.msg import PointStamped, PoseStamped, TwistStamped
from nav2_msgs.action import ComputePathToPose, NavigateToPose
from nav2_msgs.srv import ClearEntireCostmap
from action_msgs.msg import GoalStatus
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from std_msgs.msg import Bool, String
from visualization_msgs.msg import MarkerArray


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
        self.stalled = False
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.create_timer(1.0, self.check_timeout)

        self.declare_parameter('stall_timeout', 0.0)
        self.declare_parameter('stall_radius', 0.3)
        # stall_angle (rad, 0 = off): turning this much within the window also counts as progress,
        # so a U-turn on the spot is not given up as a stall (tunnel_reverse.launch.py)
        self.declare_parameter('stall_angle', 0.0)
        self.stall_angle = self.get_parameter('stall_angle').value
        self.stall_timeout = self.get_parameter('stall_timeout').value
        self.stall_radius = self.get_parameter('stall_radius').value
        self.track = []             # (t, x, y, yaw) of the robot while a goal is active
        if self.stall_timeout > 0.0:
            self.get_logger().info(f'Stall give-up on: < {self.stall_radius:.2f} m in {self.stall_timeout:.0f} s')

        self.declare_parameter('precheck_path', False)
        self.precheck = self.get_parameter('precheck_path').value
        self.plan_client = ActionClient(self, ComputePathToPose, 'compute_path_to_pose')
        self.precheck_fails = {}    # goal cell (0.5 m grid) -> failed pre-checks
        self.clear_global = self.create_client(ClearEntireCostmap, 'global_costmap/clear_entirely_global_costmap')

        self.declare_parameter('retrace_distance', 0.0)
        self.declare_parameter('retrace_speed', 0.08)
        self.declare_parameter('retrace_timeout', 30.0)
        self.declare_parameter('retrace_after_fails', 2)
        self.declare_parameter('retrace_controller', '')
        self.declare_parameter('retrace_max_moved', 0.1)
        g = lambda n: self.get_parameter(n).value
        self.retrace_dist, self.retrace_speed = g('retrace_distance'), g('retrace_speed')
        self.retrace_timeout, self.retrace_after = g('retrace_timeout'), g('retrace_after_fails')
        self.retrace_ctrl, self.retrace_max_moved = g('retrace_controller'), g('retrace_max_moved')
        self.last_retrace = None    # (t, x, y) where the last retrace started (loop guard)
        self.stall_moved = None
        self.crumbs = []            # (x, y) every 5 cm the robot drove, newest last
        self.retrace = None         # active retrace: dict, see start_retrace()
        self.fail_count, self.fail_spot = 0, None
        self.last_reached = None    # (x, y, robot pose) of the last reached goal, see check_reached_again
        self.controller = ''
        if self.retrace_dist > 0.0:
            self.cmd_pub = self.create_publisher(TwistStamped, '/cmd_vel_nav', 10)
            latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                                 reliability=ReliabilityPolicy.RELIABLE)
            self.create_subscription(String, '/controller_selector',
                                     lambda m: setattr(self, 'controller', m.data), latched)
            self.create_timer(0.1, self.retrace_step)
            self.get_logger().info(f'Retrace on: back {self.retrace_dist:.1f} m along own track when stuck'
                                   + (f' (only with {self.retrace_ctrl})' if self.retrace_ctrl else ''))

        self.declare_parameter('explored_cancel', False)
        self.explored_misses = 0
        self.explored_cancelled = False
        if self.get_parameter('explored_cancel').value:
            self.create_subscription(MarkerArray, '/frontier_markers', self.frontiers_callback, 10)
            self.get_logger().info('Explored-goal cancel on: a goal no longer near any frontier is dropped')

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

    def robot_position(self):
        try:
            t = self.tf_buffer.lookup_transform('map', 'base_footprint', rclpy.time.Time())
            q = t.transform.rotation
            yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
            return t.transform.translation.x, t.transform.translation.y, yaw
        except Exception:
            return None

    def frontiers_callback(self, msg: MarkerArray):
        if self.goal_handle is None or self.goal is None or self.retrace is not None:
            self.explored_misses = 0
            return
        g = self.goal.pose.position
        near = any(m.action == m.ADD and math.hypot(m.pose.position.x - g.x, m.pose.position.y - g.y) < 1.0
                   for m in msg.markers)
        self.explored_misses = 0 if near else self.explored_misses + 1
        if self.explored_misses >= 2:
            self.get_logger().info(f'Frontier at ({g.x:.2f}, {g.y:.2f}) explored on the way - next frontier')
            self.explored_misses = 0
            self.explored_cancelled = True
            self.deadline = None
            self.goal_handle.cancel_goal_async()

    def check_timeout(self):
        if self.deadline is None or self.goal_handle is None:
            return
        now = self.get_clock().now().nanoseconds / 1e9
        if now > self.deadline:
            self.get_logger().warn('Goal took too long - cancelling it')
            self.give_up()
            return
        if self.stall_timeout > 0.0 and (p := self.robot_position()) is not None:
            self.track.append((now, *p))
            old = [q for q in self.track if q[0] <= now - self.stall_timeout]
            if old:
                self.track = [q for q in self.track if q[0] >= old[-1][0]]
                moved = math.hypot(p[0] - old[-1][1], p[1] - old[-1][2])
                win = [q for q in self.track if q[0] >= old[-1][0]]
                turned = sum(abs(math.atan2(math.sin(b[3] - a[3]), math.cos(b[3] - a[3]))) for a, b in zip(win, win[1:]))
                if moved < self.stall_radius and not (self.stall_angle > 0.0 and turned >= self.stall_angle):
                    self.get_logger().warn(
                        f'No progress: moved {moved:.2f} m in {self.stall_timeout:.0f} s - cancelling it')
                    self.stalled = True
                    self.stall_moved = moved
                    self.give_up()

    def give_up(self):
        # counted like a timeout: result_callback blacklists the frontier
        self.timed_out = True
        self.deadline = None
        self.track = []
        self.goal_handle.cancel_goal_async()

    def goal_callback(self, msg: PoseStamped):
        if self.paused:
            return  # manual driving - no autonomous goals
        if self.busy:
            return  # already navigating - ignore updates until this leg finishes

        self.busy = True
        self.goal = msg
        self.timed_out = False
        self.stalled = False
        self.stall_moved = None
        if self.precheck and self.plan_client.server_is_ready():
            req = ComputePathToPose.Goal()
            req.goal = msg
            req.use_start = False
            self.plan_client.send_goal_async(req).add_done_callback(self.precheck_response)
            return
        self.send_nav_goal(msg)

    def precheck_response(self, future):
        handle = future.result()
        if not handle.accepted:
            self.send_nav_goal(self.goal)      # planner busy or refusing requests: let Nav2 decide
            return
        handle.get_result_async().add_done_callback(self.precheck_result)

    def precheck_result(self, future):
        res = future.result()
        if res.status == GoalStatus.STATUS_SUCCEEDED and len(res.result.path.poses) > 0:
            self.send_nav_goal(self.goal)
            return
        p = self.goal.pose.position
        key = (round(p.x * 2), round(p.y * 2))
        self.precheck_fails[key] = self.precheck_fails.get(key, 0) + 1
        if self.precheck_fails[key] >= 2:
            self.get_logger().warn(f'No path to frontier ({p.x:.2f}, {p.y:.2f}) - blacklisted, not sent')
            self.publish_blacklist()
            if self.goal_failed(stalled=False):
                return
        else:
            # one failure can be a costmap that hasn't caught up yet (seen at start-up, when
            # the global costmap refreshes at 1 Hz), or a stale obstacle near the robot: clear
            # the global costmap (the static map comes back at once) and check again in ~3 s
            self.get_logger().info(f'No path to frontier ({p.x:.2f}, {p.y:.2f}) yet - will check again')
            if self.clear_global.service_is_ready():
                self.clear_global.call_async(ClearEntireCostmap.Request())
        self.busy = False

    def check_reached_again(self):
        """A frontier inside the goal tolerance that the LiDAR can't see into stays a frontier: it was
        'reached' at once, every 3 s, 62 times in a row while the run stood still (nav-speed,
        2026-10-21). Reached twice without the robot moving 0.3 m: blacklist it."""
        p, g = self.robot_position(), self.goal.pose.position
        last, self.last_reached = self.last_reached, (g.x, g.y, p)
        if last is None or p is None or last[2] is None:
            return
        if math.hypot(g.x - last[0], g.y - last[1]) < 0.3 and math.hypot(p[0] - last[2][0], p[1] - last[2][1]) < 0.3:
            self.get_logger().warn(f'Reached frontier ({g.x:.2f}, {g.y:.2f}) again without it clearing - blacklisted')
            self.publish_blacklist()
            self.last_reached = None

    def publish_blacklist(self):
        bl = PointStamped()
        bl.header = self.goal.header
        bl.point.x, bl.point.y = self.goal.pose.position.x, self.goal.pose.position.y
        self.blacklist_pub.publish(bl)

    def send_nav_goal(self, msg: PoseStamped):
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
        self.track = []
        self.explored_misses, self.explored_cancelled = 0, False
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
            self.fail_count, self.fail_spot = 0, None
            self.check_reached_again()
        elif self.explored_cancelled:
            self.fail_count, self.fail_spot = 0, None     # not a failure: nothing left to see there
        else:
            names = {GoalStatus.STATUS_ABORTED: 'aborted', GoalStatus.STATUS_CANCELED: 'canceled'}
            reason = 'timed out' if self.timed_out else names.get(status, status)
            self.get_logger().warn(f'Nav2 gave up on the goal ({reason}) - ready for next frontier')
            # A manual-override cancel is not the frontier's fault; anything else is.
            if (status == GoalStatus.STATUS_ABORTED or self.timed_out) and self.goal is not None:
                self.publish_blacklist()
                self.goal_handle = None
                self.deadline = None
                if self.goal_failed(stalled=self.stalled):
                    return              # retracing: stays busy until it is done
        self.goal_handle = None
        self.deadline = None
        self.busy = False

    # ---------------- retrace: back out along the robot's own track ----------------
    def goal_failed(self, stalled):
        """Count a failed goal; start a retrace if stuck. True if a retrace started (stay busy)."""
        if self.retrace_dist <= 0.0 or self.paused or (p := self.robot_position()) is None:
            return False
        if self.fail_spot is None or math.hypot(p[0] - self.fail_spot[0], p[1] - self.fail_spot[1]) > 0.5:
            self.fail_count, self.fail_spot = 0, p[:2]
        self.fail_count += 1
        stuck = stalled and self.stall_moved is not None and self.stall_moved < self.retrace_max_moved
        if not (stuck or self.fail_count >= self.retrace_after):
            return False
        if self.retrace_ctrl and self.controller != self.retrace_ctrl:
            return False
        now = self.get_clock().now().nanoseconds / 1e9
        if (stuck and self.last_retrace is not None and now - self.last_retrace[0] < 300.0 and
                math.hypot(p[0] - self.last_retrace[1], p[1] - self.last_retrace[2]) < 0.5):
            self.get_logger().info('Stuck again where the last retrace started - not retracing again')
            return False
        return self.start_retrace(p, f'moved {self.stall_moved:.2f} m' if stuck else f'{self.fail_count} failed goals here')

    def start_retrace(self, p, why):
        # walk back along the crumbs (newest first) until retrace_distance of track is covered
        pts, run, last = [], 0.0, p[:2]
        for c in reversed(self.crumbs):
            run += math.hypot(c[0] - last[0], c[1] - last[1]); last = c
            pts.append(c)
            if run >= self.retrace_dist:
                break
        pts = [c for c in pts if math.hypot(c[0] - p[0], c[1] - p[1]) > 0.1] or pts
        if run < 0.3:
            self.get_logger().warn(f'Stuck ({why}) but no recorded track to back out along')
            return False
        # drive backwards if the track leads behind the robot (it drove in forwards), else forwards
        a = math.atan2(pts[min(3, len(pts) - 1)][1] - p[1], pts[min(3, len(pts) - 1)][0] - p[0]) - p[2]
        sign = -1.0 if math.cos(a) < 0.0 else 1.0
        now = self.get_clock().now().nanoseconds / 1e9
        self.retrace = {'pts': pts, 'i': 0, 'sign': sign, 't0': now, 'moved_t': now, 'moved_p': p[:2]}
        self.last_retrace = (now, p[0], p[1])
        self.fail_count, self.fail_spot = 0, None
        self.get_logger().warn(f'Stuck ({why}) - retracing {run:.1f} m of own track '
                               f'{"backwards" if sign < 0 else "forwards"}')
        return True

    def retrace_step(self):
        p = self.robot_position()
        if p is None:
            return
        r = self.retrace
        if r is None:
            # record the track (not while retracing, so a second retrace goes further back)
            if not self.crumbs or math.hypot(p[0] - self.crumbs[-1][0], p[1] - self.crumbs[-1][1]) >= 0.05:
                self.crumbs = (self.crumbs + [p[:2]])[-400:]          # last ~20 m
            return
        now = self.get_clock().now().nanoseconds / 1e9
        pts = r['pts']
        while r['i'] < len(pts) - 1 and math.hypot(pts[r['i']][0] - p[0], pts[r['i']][1] - p[1]) < 0.25:
            r['i'] += 1
        if math.hypot(p[0] - r['moved_p'][0], p[1] - r['moved_p'][1]) > 0.05:
            r['moved_t'], r['moved_p'] = now, p[:2]
        tx, ty = pts[r['i']]
        done = r['i'] == len(pts) - 1 and math.hypot(tx - p[0], ty - p[1]) < 0.15
        if done or now - r['moved_t'] > 6.0 or now - r['t0'] > self.retrace_timeout or self.paused:
            reason = 'done' if done else 'paused' if self.paused else 'blocked' if now - r['moved_t'] > 6.0 else 'timeout'
            self.cmd_pub.publish(TwistStamped())
            # forget the retraced part of the track, so a second retrace goes further back
            k = min(range(len(self.crumbs)), key=lambda j: math.hypot(self.crumbs[j][0] - p[0], self.crumbs[j][1] - p[1]))
            self.crumbs = self.crumbs[:k + 1]
            self.get_logger().info(f'Retrace {reason} - ready for next frontier')
            self.retrace = None
            self.busy = False
            return
        # pure pursuit on the track; err = angle between the driving direction and the target
        err = math.atan2(ty - p[1], tx - p[0]) - p[2]
        if r['sign'] < 0:
            err += math.pi
        err = math.atan2(math.sin(err), math.cos(err))
        cmd = TwistStamped()
        cmd.header.stamp = self.get_clock().now().to_msg()
        cmd.header.frame_id = 'base_footprint'
        cmd.twist.linear.x = r['sign'] * self.retrace_speed * max(0.0, math.cos(err)) ** 2
        cmd.twist.angular.z = max(-0.5, min(0.5, 1.5 * err))
        self.cmd_pub.publish(cmd)


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
