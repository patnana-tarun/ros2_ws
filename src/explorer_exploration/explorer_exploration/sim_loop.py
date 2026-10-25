"""
Endless simulation loop for testing the mesh relay: keeps /map and /tf flowing until Ctrl-C.

    ros2 launch explorer_exploration sim_loop.launch.py

Starts `ros2 launch explorer_exploration <sim_launch> <sim_args>` as a child, watches /map and,
when true-floor coverage reaches target_pct, shuts the whole sim down (Gazebo, RViz, SLAM, Nav2)
and starts a fresh one. A run is also restarted when:
  - the sim launch exits on its own (crash),
  - no /map arrives within startup_timeout_s,
  - /exploration_complete arrives below target_pct (the robot would sit still),
  - coverage gains < 0.5 m2 in stall_restart_s (0 = never).

Coverage is the measure the rover tools and experiments use (rosview.py coverage()): map cells
that are known (free or occupied) over the cave's true floor area from field_file. field.npz is
made for cave.sdf, so the percentage is wrong for another world.

Every child process gets SIM_LOOP_ID=<this pid> in its environment; the stop step kills
anything left with that marker (gz sim sometimes outlives its launch), and the start-up step
kills leftovers from an earlier sim_loop that was itself killed. Each run is one CSV row in
cycle_log (wall-clock start/end), so restart gaps can be cut out of the communication metrics.
Timing is wall clock, so the sim's clock going back to 0 on a restart does not matter.
"""

import csv
import datetime
import os
import shlex
import signal
import subprocess
import time

import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import Empty

MARKER = 'SIM_LOOP_ID'
STALL_GAIN_M2 = 0.5


def marked_pids(keep=None):
    """PIDs whose environment has the SIM_LOOP_ID marker (value != keep if keep is given)."""
    out = []
    for p in os.listdir('/proc'):
        if not p.isdigit() or int(p) == os.getpid():
            continue
        try:
            with open(f'/proc/{p}/environ', 'rb') as f:
                env = f.read().split(b'\0')
        except Exception:
            continue
        for e in env:
            if e.startswith(MARKER.encode() + b'='):
                if keep is None or e != f'{MARKER}={keep}'.encode():
                    out.append(int(p))
                break
    return out


def kill_all(pids):
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


class SimLoop(Node):
    def __init__(self):
        super().__init__('sim_loop')
        self.declare_parameter('sim_launch', 'tunnel_reverse.launch.py')
        self.declare_parameter('sim_args', '')
        self.declare_parameter('target_pct', 85.0)
        self.declare_parameter('stall_restart_s', 300.0)
        self.declare_parameter('startup_timeout_s', 180.0)
        self.declare_parameter('restart_delay_s', 5.0)
        self.declare_parameter('field_file',
                               os.path.expanduser('~/ros2_ws/data/demo_runs_2026-10-19/field.npz'))
        self.declare_parameter('cycle_log', os.path.expanduser('~/.ros/sim_loop_cycles.csv'))
        g = lambda n: self.get_parameter(n).value  # noqa: E731
        self.sim_launch, self.sim_args = g('sim_launch'), g('sim_args')
        self.target = float(g('target_pct'))
        self.stall_s = float(g('stall_restart_s'))
        self.startup_s = float(g('startup_timeout_s'))
        self.delay_s = float(g('restart_delay_s'))
        self.cycle_log = g('cycle_log')

        f = np.load(g('field_file'))
        self.floor = f['s'] < 0
        self.f_res, self.f_x0, self.f_y0 = float(f['res']), float(f['XMIN']), float(f['YMIN'])
        self.floor_m2 = float(self.floor.sum()) * self.f_res ** 2

        old = marked_pids(keep=os.getpid())
        if old:
            self.get_logger().warn(f'Killing {len(old)} processes left by an earlier sim_loop')
            kill_all(old)
            time.sleep(1.0)

        map_qos = QoSProfile(depth=1)
        map_qos.reliability = ReliabilityPolicy.RELIABLE
        map_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(OccupancyGrid, '/map', self.map_cb, map_qos)
        self.create_subscription(Empty, '/exploration_complete', self.complete_cb, 10)

        self.proc = None
        self.cycle = 0
        self.start_run()
        self.create_timer(1.0, self.tick)

    # ------------------------------------------------------------ coverage
    def coverage(self, m):
        """(true-floor coverage m2, %) - same measure as tools/rover_mcp/rosview.py."""
        a = np.asarray(m.data, dtype=np.int16).reshape(m.info.height, m.info.width)
        res = m.info.resolution
        iy, ix = np.nonzero(a >= 0)
        wx = m.info.origin.position.x + (ix + 0.5) * res
        wy = m.info.origin.position.y + (iy + 0.5) * res
        gi = np.floor((wy - self.f_y0) / self.f_res + 0.5).astype(int)
        gj = np.floor((wx - self.f_x0) / self.f_res + 0.5).astype(int)
        ok = (gi >= 0) & (gi < self.floor.shape[0]) & (gj >= 0) & (gj < self.floor.shape[1])
        seen = np.zeros(self.floor.shape, bool)
        seen[gi[ok], gj[ok]] = True
        c = float((seen & self.floor).sum()) * self.f_res ** 2
        return c, 100.0 * c / self.floor_m2

    def map_cb(self, msg):
        if self.proc is None:
            return
        self.cov_m2, self.cov_pct = self.coverage(msg)
        now = time.monotonic()
        if self.first_map is None:
            self.first_map = now
            self.get_logger().info(f'Run {self.cycle}: first /map after {now - self.t0:.0f} s')
        if self.cov_m2 >= self.stall_ref_m2 + STALL_GAIN_M2:
            self.stall_ref_m2, self.stall_ref_t = self.cov_m2, now
        if self.cov_pct >= self.next_report:
            self.get_logger().info(f'Run {self.cycle}: coverage {self.cov_pct:.1f} %')
            self.next_report = 10.0 * (self.cov_pct // 10.0 + 1)

    def complete_cb(self, _msg):
        if self.proc is not None and self.first_map is not None:
            self.complete = True

    # ------------------------------------------------------------ run control
    def start_run(self):
        self.cycle += 1
        env = os.environ.copy()
        env[MARKER] = str(os.getpid())
        argv = ['ros2', 'launch', 'explorer_exploration', self.sim_launch] + shlex.split(self.sim_args)
        self.get_logger().info(f'Run {self.cycle}: starting {" ".join(argv)}')
        self.proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, start_new_session=True, env=env)
        self.t0 = time.monotonic()
        self.start_wall = datetime.datetime.now()
        self.first_map = None
        self.cov_m2, self.cov_pct = 0.0, 0.0
        self.stall_ref_m2, self.stall_ref_t = 0.0, self.t0
        self.next_report = 10.0
        self.complete = False

    def stop_run(self, reason, grace=10.0):
        p, self.proc = self.proc, None
        if p is None:
            return
        self.get_logger().info(
            f'Run {self.cycle}: stopping ({reason}) at {self.cov_pct:.1f} % after '
            f'{(time.monotonic() - self.t0) / 60:.1f} min')
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGINT)
                p.wait(grace)
            except Exception:
                pass
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            pass
        kill_all(marked_pids())
        try:
            p.wait(2.0)
        except Exception:
            pass
        self.log_cycle(reason)

    def log_cycle(self, reason):
        new = not os.path.exists(self.cycle_log)
        os.makedirs(os.path.dirname(self.cycle_log) or '.', exist_ok=True)
        with open(self.cycle_log, 'a', newline='') as f:
            w = csv.writer(f)
            if new:
                w.writerow(['run', 'start', 'end', 'duration_s', 'first_map_s', 'coverage_pct',
                            'reason', 'sim_launch', 'sim_args'])
            w.writerow([self.cycle, self.start_wall.isoformat(timespec='seconds'),
                        datetime.datetime.now().isoformat(timespec='seconds'),
                        round(time.monotonic() - self.t0),
                        round(self.first_map - self.t0) if self.first_map else '',
                        round(self.cov_pct, 1), reason, self.sim_launch, self.sim_args])

    def tick(self):
        if self.proc is None:
            return
        now = time.monotonic()
        reason = None
        if self.proc.poll() is not None:
            reason = f'launch_exited_{self.proc.returncode}'
        elif self.cov_pct >= self.target:
            reason = f'reached_{self.target:g}'
        elif self.first_map is None and now - self.t0 > self.startup_s:
            reason = 'no_map'
        elif self.complete:
            reason = 'exploration_complete'
        elif self.stall_s > 0 and self.first_map is not None and now - self.stall_ref_t > self.stall_s:
            reason = 'stalled'
        if reason is None:
            return
        self.stop_run(reason)
        time.sleep(self.delay_s)
        if rclpy.ok():      # not Ctrl-C'd during the restart
            self.start_run()

    def shutdown(self):
        # ros2 launch follows Ctrl-C with SIGTERM after 5 s: finish the cleanup regardless
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        self.stop_run('user_stop', grace=4.0)


def _raise_interrupt(*_):
    raise KeyboardInterrupt


def main(args=None):
    rclpy.init(args=args)
    node = SimLoop()
    signal.signal(signal.SIGTERM, _raise_interrupt)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
