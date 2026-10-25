#!/usr/bin/env python3
"""Per-run recorder for the NavFn vs Smac Lattice A/B. Starts at the first /plan, runs DUR s of sim time."""
import math, sys, time, json
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from rclpy.time import Time
from nav_msgs.msg import Path, Odometry, OccupancyGrid
from geometry_msgs.msg import TwistStamped
from nav2_msgs.srv import IsPathValid
import tf2_ros

DUR = float(sys.argv[1]); OUT = sys.argv[2]


def yaw_q(q): return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def resample(pts, step=0.10):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    if d[-1] < step: return pts[[0, -1]], d[-1]
    s = np.arange(0, d[-1], step)
    return np.c_[np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])], d[-1]


class R(Node):
    def __init__(self):
        super().__init__('bench_recorder', parameter_overrides=[rclpy.Parameter('use_sim_time', value=True)])
        tl = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
        self.buf = tf2_ros.Buffer(); self.tl = tf2_ros.TransformListener(self.buf, self)
        self.cli = self.create_client(IsPathValid, 'is_path_valid')
        self.t0 = None; self.gcm = None
        self.area = []; self.dist = 0.0; self.last_xy = None
        self.plans = []; self.prev_plan = None; self.pending = []
        self.cmd = []; self.xte = []
        self.create_subscription(OccupancyGrid, 'map', self.on_map, tl)
        self.create_subscription(OccupancyGrid, 'global_costmap/costmap', lambda m: setattr(self, 'gcm', m), tl)
        self.create_subscription(Odometry, 'odom', self.on_odom, 20)
        self.create_subscription(Path, 'plan', self.on_plan, 10)
        self.create_subscription(TwistStamped, 'cmd_vel_nav', self.on_cmd, 20)
        self.cur = None
        self.create_timer(0.1, self.tick)

    def st(self): return self.get_clock().now().nanoseconds / 1e9

    def el(self): return None if self.t0 is None else self.st() - self.t0

    def on_map(self, m):
        a = np.array(m.data); r2 = m.info.resolution ** 2
        self.area.append((self.el(), float((a == 0).sum() * r2), float((a >= 0).sum() * r2)))

    def on_odom(self, m):
        p = m.pose.pose.position
        if self.t0 is not None and self.last_xy is not None:
            self.dist += math.hypot(p.x - self.last_xy[0], p.y - self.last_xy[1])
        self.last_xy = (p.x, p.y)

    def on_cmd(self, m):
        if self.t0 is not None: self.cmd.append((self.el(), m.twist.linear.x, m.twist.angular.z))

    def fp_cost(self, x, y, yaw):
        c = self.gcm; W, H, r = c.info.width, c.info.height, c.info.resolution
        ox, oy = c.info.origin.position.x, c.info.origin.position.y
        ca, sa = math.cos(yaw), math.sin(yaw); mx = 0
        for fx in (-0.16, -0.08, 0.0, 0.08, 0.16):
            for fy in (-0.11, -0.055, 0.0, 0.055, 0.11):
                i = int((x + ca * fx - sa * fy - ox) / r); j = int((y + sa * fx + ca * fy - oy) / r)
                if 0 <= i < W and 0 <= j < H:
                    v = c.data[j * W + i]; mx = max(mx, v)
        return mx

    def on_plan(self, m):
        if len(m.poses) < 2: return
        if self.t0 is None: self.t0 = self.st(); self.get_logger().info('recording')
        pts = np.array([[p.pose.position.x, p.pose.position.y] for p in m.poses])
        rs, L = resample(pts)
        h = np.unwrap(np.arctan2(np.diff(rs[:, 1]), np.diff(rs[:, 0]))) if len(rs) > 2 else np.array([0.0])
        turn = float(np.abs(np.diff(h)).sum()) if len(h) > 1 else 0.0
        jerks = int((np.abs(np.diff(h)) > math.radians(30)).sum()) if len(h) > 1 else 0
        fpc = []
        if self.gcm is not None:
            for k in range(len(rs) - 1):
                fpc.append(self.fp_cost(rs[k, 0], rs[k, 1], math.atan2(rs[k + 1, 1] - rs[k, 1], rs[k + 1, 0] - rs[k, 0])))
        fpc = np.array(fpc) if fpc else np.array([0])
        nz = sum(1 for p in m.poses if abs(p.pose.orientation.z) > 1e-3)
        row = {'t': self.el(), 'len': float(L), 'turn_per_m': turn / max(L, 0.1), 'kinks30': jerks,
               'fp_max': int(fpc.max()), 'fp_frac_ge99': float((fpc >= 99).mean()), 'fp_frac_ge50': float((fpc >= 50).mean()),
               'fp_mean': float(fpc.mean()), 'heading_poses': nz / len(m.poses), 'goal': pts[-1].tolist()}
        if self.prev_plan is not None and self.cli.service_is_ready():
            req = IsPathValid.Request(); req.path = self.prev_plan
            self.pending.append((row, self.cli.call_async(req)))
        self.prev_plan = m; self.cur = rs; self.plans.append(row)

    def tick(self):
        for r, f in list(self.pending):
            if f.done():
                try: r['prev_valid'] = bool(f.result().is_valid)
                except Exception: pass
                self.pending.remove((r, f))
        if self.cur is None or self.t0 is None: return
        try: mb = self.buf.lookup_transform('map', 'base_footprint', Time())
        except Exception: return
        p = np.array([mb.transform.translation.x, mb.transform.translation.y]); best = 9e9
        for k in range(len(self.cur) - 1):
            a, b = self.cur[k], self.cur[k + 1]; ab = b - a; L = ab @ ab
            t = 0 if L == 0 else max(0, min(1, ((p - a) @ ab) / L))
            best = min(best, float(np.linalg.norm(p - (a + t * ab))))
        self.xte.append((self.el(), best))


def main():
    rclpy.init(); n = R(); w0 = None
    while rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.05)
        if n.el() is not None and w0 is None: w0 = time.monotonic()
        if n.el() is not None and n.el() > DUR: break
    json.dump({'area': n.area, 'dist': n.dist, 'plans': n.plans, 'cmd': n.cmd, 'xte': n.xte, 'dur': n.el(), 'wall_s': time.monotonic() - w0 if w0 else None}, open(OUT, 'w'))
    print('done', OUT, 'plans', len(n.plans), 'dist %.1f' % n.dist)


main()
