#!/usr/bin/env python3
"""Recorder for the tunnel-tracking runs (exp/tunnel-tracking, 2026-10-18).

Starts at the first /plan and records DUR s of sim time:
- 10 Hz pose samples in the map frame, with heading deviation from the path the controller
  follows (/plan_smoothed when the smoother is in use, else /plan), cross-track error,
  corridor width from the LiDAR (left + right clearance at +-90 deg), and odometry vx / wz
- explored area over time, /cmd_vel_nav, every path, the final /map (for trajectory figures)
Usage: tunnel_recorder.py DUR OUT_PREFIX   ->  OUT_PREFIX.json, OUT_PREFIX_map.npz
"""
import math, sys, time, json
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from rclpy.time import Time
from nav_msgs.msg import Path, Odometry, OccupancyGrid
from geometry_msgs.msg import TwistStamped
from sensor_msgs.msg import LaserScan
import tf2_ros

DUR = float(sys.argv[1]); OUT = sys.argv[2]


def yaw_q(q): return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def wrap(a): return (a + math.pi) % (2 * math.pi) - math.pi


def resample(pts, step=0.05):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    if d[-1] < step: return pts
    s = np.arange(0, d[-1] + 1e-9, step)
    return np.c_[np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])]


class Rec(Node):
    def __init__(self):
        super().__init__('tunnel_recorder', parameter_overrides=[rclpy.Parameter('use_sim_time', value=True)])
        tl = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
        self.buf = tf2_ros.Buffer(); self.tl = tf2_ros.TransformListener(self.buf, self)
        self.t0 = None; self.w0 = None
        self.paths = {'plan': None, 'plan_smoothed': None}; self.path_t = {'plan': -1e9, 'plan_smoothed': -1e9}
        self.path_log = []; self.area = []; self.map = None; self.cmd = []
        self.odom = (0.0, 0.0); self.width = float('nan'); self.samples = []
        self.create_subscription(Path, 'plan', lambda m: self.on_path(m, 'plan'), 10)
        self.create_subscription(Path, 'plan_smoothed', lambda m: self.on_path(m, 'plan_smoothed'), 10)
        self.create_subscription(OccupancyGrid, 'map', self.on_map, tl)
        self.create_subscription(Odometry, 'odom', lambda m: setattr(self, 'odom', (m.twist.twist.linear.x, m.twist.twist.angular.z)), 20)
        self.create_subscription(TwistStamped, 'cmd_vel_nav', self.on_cmd, 20)
        self.create_subscription(LaserScan, 'scan', self.on_scan, qos_profile_sensor_data)
        self.create_timer(0.1, self.tick)

    def el(self): return None if self.t0 is None else self.get_clock().now().nanoseconds / 1e9 - self.t0

    def on_path(self, m, src):
        if len(m.poses) < 2: return
        if self.t0 is None:
            self.t0 = self.get_clock().now().nanoseconds / 1e9; self.w0 = time.time()
            self.get_logger().info('recording')
        pts = np.array([[p.pose.position.x, p.pose.position.y] for p in m.poses])
        self.paths[src] = resample(pts); self.path_t[src] = self.el()
        # path shape, for the record
        rs = resample(pts, 0.10)
        h = np.unwrap(np.arctan2(np.diff(rs[:, 1]), np.diff(rs[:, 0]))) if len(rs) > 2 else np.zeros(1)
        L = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
        dh = np.abs(np.diff(h)) if len(h) > 1 else np.zeros(1)
        self.path_log.append({'t': self.el(), 'src': src, 'len': L, 'turn_deg_per_m': math.degrees(dh.sum()) / max(L, 0.1),
                              'kinks30_per_m': float((dh > math.radians(30)).sum()) / max(L, 0.1),
                              'pts': rs[::2].round(3).tolist()})

    def on_map(self, m):
        self.map = m
        if self.t0 is not None:
            a = np.array(m.data); r2 = m.info.resolution ** 2
            self.area.append((self.el(), float((a == 0).sum() * r2)))

    def on_cmd(self, m):
        if self.t0 is not None: self.cmd.append((self.el(), m.twist.linear.x, m.twist.angular.z))

    def on_scan(self, m):
        r = np.array(m.ranges, float); r[~np.isfinite(r)] = m.range_max
        ang = m.angle_min + np.arange(len(r)) * m.angle_increment
        def side(c):
            k = np.abs(np.angle(np.exp(1j * (ang - c)))) < math.radians(10)
            return float(r[k].min()) if k.any() else float('nan')
        self.width = side(math.pi / 2) + side(-math.pi / 2)   # scan frame: +y left

    def active_path(self):
        # the controller follows the smoothed path when the smoother runs (it arrives just after /plan)
        if self.paths['plan_smoothed'] is not None and self.path_t['plan_smoothed'] >= self.path_t['plan'] - 1.0:
            return self.paths['plan_smoothed'], 'smoothed'
        return self.paths['plan'], 'raw'

    def tick(self):
        if self.t0 is None: return
        try: mb = self.buf.lookup_transform('map', 'base_footprint', Time())
        except Exception: return
        x, y, yaw = mb.transform.translation.x, mb.transform.translation.y, yaw_q(mb.transform.rotation)
        s = {'t': round(self.el(), 2), 'w': round(time.time() - self.w0, 2), 'x': round(x, 3), 'y': round(y, 3),
             'yaw': round(yaw, 4), 'vx': round(self.odom[0], 3), 'wz': round(self.odom[1], 3), 'width': round(self.width, 3)}
        P, src = self.active_path()
        if P is not None and len(P) > 2:
            d = np.hypot(P[:, 0] - x, P[:, 1] - y); k = int(np.argmin(d)); k = min(k, len(P) - 2)
            tang = math.atan2(P[k + 1, 1] - P[k, 1], P[k + 1, 0] - P[k, 0])
            s['xte'] = round(float(d.min()), 3); s['hdev'] = round(math.degrees(wrap(yaw - tang)), 1); s['src'] = src
        self.samples.append(s)


def main():
    rclpy.init(); n = Rec(); start = time.time()
    while rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.05)
        if n.el() is not None and n.el() > DUR: break
        if n.t0 is None and time.time() - start > 240:      # the sim never started exploring
            print('no plan within 240 s - giving up'); sys.exit(2)
    m = n.map
    if m is not None:
        np.savez_compressed(OUT + '_map.npz', data=np.array(m.data, np.int8).reshape(m.info.height, m.info.width),
                            res=m.info.resolution, ox=m.info.origin.position.x, oy=m.info.origin.position.y)
    json.dump({'samples': n.samples, 'area': n.area, 'cmd': n.cmd, 'paths': n.path_log,
               'dur': n.el(), 'wall_s': time.time() - n.w0 if n.w0 else None, 'wall_start': n.w0}, open(OUT + '.json', 'w'))
    print('done', OUT, 'samples', len(n.samples), 'paths', len(n.path_log))


main()
