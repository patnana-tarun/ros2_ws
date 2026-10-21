"""Live ROS view for the rover MCP server and the experiment harness: one rclpy node that keeps
what tuning needs, computes the tuning metrics, and raises health alerts.

Kept:
- 10 Hz samples (steady clock, stamped with sim time): map->base_footprint pose, odom vx/wz, last
  /cmd_vel_nav, active controller, cross-track and heading error to the path the controller follows
  (/plan_smoothed if fresh, else /plan; as demo_recorder.py), front clearance, corridor width
- every /plan with its share of points on unknown and on lethal/inscribed global-costmap cells
- /map, /global_costmap/costmap, /best_goal history, controller switches, message rates
- /rosout of every node (ring buffer); goal outcomes parsed from explore_coordinator's messages

Metric definitions follow docs/demo_runs_2026-10-19/validate.py and the tunnel-reverse analysis,
so live numbers compare with the report: stuck = < 0.5 m net over the surrounding 60 s; tunnel =
LiDAR left+right < 1.2 m, open > 2.0 m; tracking uses forward (vx > 0.05), not-stuck samples;
large deviation = xte > 0.10 m or |heading| > 30 deg; rotation event = >= 300 deg of turning
within 60 s while the robot drives < 1 m (path length; user's decision 2026-10-21, was < 1 m net
displacement: that also counted out-and-back trips into short pockets, which are not spinning;
the old count stays as rotation_events_net).
"""
import collections
import io
import math
import os
import re
import threading
import time

import numpy as np
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from rclpy.time import Time
from rosidl_runtime_py.utilities import get_message
import tf2_ros

LEVELS = {10: 'DEBUG', 20: 'INFO', 30: 'WARN', 40: 'ERROR', 50: 'FATAL'}
WANT = ['/map', '/odom', '/plan', '/plan_smoothed', '/best_goal', '/cmd_vel_nav', '/controller_selector',
        '/scan', '/global_costmap/costmap', '/rosout', '/exploration_complete', '/manual_override']
FIELD = os.environ.get('ROVER_MCP_FIELD',
                       os.path.expanduser('~/ros2_ws/docs/demo_runs_2026-10-19/field.npz'))
ROBOT_R = 0.22
# expected rates: scan 7 Hz (URDF), controller 15 Hz (nav2 params); alert well below
MIN_HZ = {'/scan': 4.0, '/odom': 10.0, '/cmd_vel_nav': 10.0}
GOAL_EVENTS = [('sent', r'Sending goal'), ('reached', r'Reached goal'), ('gave_up', r'Nav2 gave up'),
               ('timeout', r'Goal took too long'), ('no_progress', r'No progress: moved'),
               ('no_path_blacklisted', r'No path to frontier .* blacklisted'), ('rejected', r'Goal rejected'),
               # "retracing" alone also matches "not retracing again" (nav-lessons)
               ('retrace_refused', r'not retracing again'), ('retrace', r'of own track'),
               ('retrace_end', r'^Retrace .* ready for next frontier'), ('stuck_no_track', r'no recorded track'),
               ('explored', r'explored on the way'), ('reached_again', r'again without it clearing')]
ALERTS_STOP = ('not_moving', 'rotation', 'node_died', 'no_map', 'no_pose', 'no_clock', 'launch_exited')


def yaw_q(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def _grid(m):
    return np.asarray(m.data, dtype=np.int16).reshape(m.info.height, m.info.width)


def _r(v, n=3):
    return None if v is None or not np.isfinite(v) else round(float(v), n)


class Watcher(Node):
    def __init__(self):
        sim = os.environ.get('ROVER_MCP_SIM_TIME', '1') == '1'
        super().__init__(f'rover_watcher_{os.getpid()}',
                         parameter_overrides=[rclpy.Parameter('use_sim_time', value=sim)])
        self.lock = threading.RLock()
        self.subs = {}
        self.buf = tf2_ros.Buffer()
        self.tfl = tf2_ros.TransformListener(self.buf, self, spin_thread=False)
        self.field = None
        if os.path.exists(FIELD):
            f = np.load(FIELD)
            self.field = dict(floor=f['s'] < 0, res=float(f['res']), x0=float(f['XMIN']), y0=float(f['YMIN']))
            self.field['m2'] = float(self.field['floor'].sum()) * self.field['res'] ** 2
        self.launch_log = None
        self.reset()
        steady = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.1, self.tick, clock=steady)
        self.create_timer(1.0, self.discover, clock=steady)

    # ------------------------------------------------------------ state
    def reset(self, launch_log=None):
        with self.lock:
            if hasattr(self, 'buf'):
                self.buf.clear()        # a new Gazebo restarts sim time; old transforms would look newest
            self.launch_log = launch_log
            self.log_off = 0
            self.died = []
            self.samples = collections.deque(maxlen=60000)
            self.rosout = collections.deque(maxlen=10000)
            self.events = []
            self.plans = collections.deque(maxlen=5000)
            # diagnostic only (not a metric): for plans with points on -1 costmap cells, how many were
            # outside the costmap bounds vs unknown inside it, and how old our costmap copy was
            self.plan_unknown_detail = []
            self.unknown_recheck = []   # [(index in plan_unknown_detail, pts)] waiting for a newer costmap
            self.costmap_t = None
            self.goals = []
            self.ctrl_log = []
            self.cov = collections.deque(maxlen=20000)
            self.rates = collections.defaultdict(lambda: collections.deque(maxlen=400))
            self.map = self.costmap = None
            self.map_wall = None
            self.paths = {'plan': None, 'plan_smoothed': None}
            self.path_t = {'plan': -1e9, 'plan_smoothed': -1e9}
            self.first_plan_t = None
            self.odom = (0.0, 0.0)
            self.cmd = (0.0, 0.0, -1e9)
            self.ctrl = None
            self.scan = (float('nan'), float('nan'))
            self.complete_t = None
            self.override = False
            self.last_sim = None
            self.last_sim_change = time.time()
            self.reset_wall = time.time()

    def now(self):
        return self.get_clock().now().nanoseconds / 1e9

    def _hit(self, topic):
        self.rates[topic].append(time.time())

    def hz(self, topic, window=5.0):
        q = self.rates.get(topic)
        if not q:
            return 0.0
        t = time.time()
        n = sum(1 for x in q if x >= t - window)
        return n / window

    # ------------------------------------------------------------ subscriptions
    def discover(self):
        try:
            types = dict(self.get_topic_names_and_types())
        except Exception:
            return
        for topic in WANT:
            if topic in self.subs or topic not in types:
                continue
            try:
                cls = get_message(types[topic][0])
            except Exception:
                continue
            if topic == '/scan':
                qos = qos_profile_sensor_data
            else:
                pubs = self.get_publishers_info_by_topic(topic)
                if not pubs:
                    continue
                qos = QoSProfile(depth=10)
                latched = any(p.qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL for p in pubs)
                be = any(p.qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT for p in pubs)
                qos.durability = DurabilityPolicy.TRANSIENT_LOCAL if latched else DurabilityPolicy.VOLATILE
                qos.reliability = ReliabilityPolicy.BEST_EFFORT if be else ReliabilityPolicy.RELIABLE
                if topic in ('/map', '/global_costmap/costmap'):
                    qos.depth = 1
            cb = getattr(self, 'on_' + topic.strip('/').replace('/', '_'))
            self.subs[topic] = self.create_subscription(cls, topic, cb, qos)

    def on_map(self, m):
        self._hit('/map')
        with self.lock:
            self.map = m
            self.map_wall = time.time()
            if self.field is not None:
                self.cov.append((self.now(),) + self.coverage(m))

    def on_global_costmap_costmap(self, m):
        with self.lock:
            self.costmap = m
            self.costmap_t = self.now()
            for k, pts in self.unknown_recheck:      # same plan against the next costmap
                unk, _ = self.path_space(pts)
                self.plan_unknown_detail[k] = self.plan_unknown_detail[k] + (int(round(unk * len(pts))),)
            self.unknown_recheck = []

    def on_odom(self, m):
        self._hit('/odom')
        self.odom = (m.twist.twist.linear.x, m.twist.twist.angular.z)

    def on_cmd_vel_nav(self, m):
        self._hit('/cmd_vel_nav')
        t = getattr(m, 'twist', m)
        self.cmd = (t.linear.x, t.angular.z, self.now())

    def on_controller_selector(self, m):
        with self.lock:
            if m.data != self.ctrl:
                self.ctrl_log.append((self.now(), m.data))
            self.ctrl = m.data

    def on_best_goal(self, m):
        x, y = m.pose.position.x, m.pose.position.y
        with self.lock:
            if not self.goals or math.hypot(x - self.goals[-1][1], y - self.goals[-1][2]) > 1e-3:
                self.goals.append((self.now(), x, y))

    def on_exploration_complete(self, m):
        if self.complete_t is None:
            self.complete_t = self.now()

    def on_manual_override(self, m):
        self.override = bool(m.data)

    def on_scan(self, m):
        self._hit('/scan')
        r = np.asarray(m.ranges, float)
        r[~np.isfinite(r)] = m.range_max
        ang = m.angle_min + np.arange(len(r)) * m.angle_increment

        def sector(c, half):
            k = np.abs(np.angle(np.exp(1j * (ang - c)))) < math.radians(half)
            return float(r[k].min()) if k.any() else float('nan')
        self.scan = (sector(0.0, 30), sector(math.pi / 2, 10) + sector(-math.pi / 2, 10))

    def on_rosout(self, m):
        t = self.now()
        with self.lock:
            self.rosout.append((t, time.time(), m.level, m.name, m.msg))
            if 'explore_coordinator' in m.name:
                for kind, rx in GOAL_EVENTS:
                    if re.search(rx, m.msg):
                        self.events.append((t, kind, m.msg[:160]))
                        break

    def _on_path(self, m, key):
        self._hit('/' + key)
        pts = np.array([[p.pose.position.x, p.pose.position.y] for p in m.poses]) if m.poses else None
        with self.lock:
            self.paths[key] = pts
            self.path_t[key] = self.now()
            if key == 'plan' and pts is not None and len(pts) > 1:
                if self.first_plan_t is None:
                    self.first_plan_t = self.now()
                L = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
                unk, leth = self.path_space(pts)
                self.plans.append((self.now(), L, unk, leth))
                if unk > 0:
                    self.plan_unknown_detail.append(self._unknown_detail(pts))
                    self.unknown_recheck.append((len(self.plan_unknown_detail) - 1, pts))

    def on_plan(self, m):
        self._on_path(m, 'plan')

    def on_plan_smoothed(self, m):
        self._on_path(m, 'plan_smoothed')

    def _unknown_detail(self, pts):
        c = self.costmap
        g = _grid(c)
        res, ox, oy = c.info.resolution, c.info.origin.position.x, c.info.origin.position.y
        j = np.floor((pts[:, 0] - ox) / res).astype(int)
        i = np.floor((pts[:, 1] - oy) / res).astype(int)
        ok = (i >= 0) & (i < g.shape[0]) & (j >= 0) & (j < g.shape[1])
        inb = np.zeros(len(pts), bool)
        inb[ok] = g[i[ok], j[ok]] < 0
        bad = inb | ~ok
        return (self.now(), int((~ok).sum()), int(inb.sum()), int(bad[-1]), int(np.nonzero(bad)[0][0]), len(pts),
                round(self.now() - self.costmap_t, 2) if self.costmap_t is not None else -1.0)

    def path_space(self, pts):
        c = self.costmap
        if c is None:
            return float('nan'), float('nan')
        g = _grid(c)
        res, ox, oy = c.info.resolution, c.info.origin.position.x, c.info.origin.position.y
        j = np.floor((pts[:, 0] - ox) / res).astype(int)
        i = np.floor((pts[:, 1] - oy) / res).astype(int)
        ok = (i >= 0) & (i < g.shape[0]) & (j >= 0) & (j < g.shape[1])
        v = np.full(len(pts), -1, np.int16)
        v[ok] = g[i[ok], j[ok]]
        return float((v < 0).mean()), float((v >= 99).mean())

    def coverage(self, m):
        """(known free m2, true-floor coverage m2, %) - same measure as demo_recorder.py."""
        a = _grid(m)
        res = m.info.resolution
        free = float((a == 0).sum()) * res ** 2
        F = self.field
        iy, ix = np.nonzero(a >= 0)
        wx = m.info.origin.position.x + (ix + 0.5) * res
        wy = m.info.origin.position.y + (iy + 0.5) * res
        gi = np.floor((wy - F['y0']) / F['res'] + 0.5).astype(int)
        gj = np.floor((wx - F['x0']) / F['res'] + 0.5).astype(int)
        ok = (gi >= 0) & (gi < F['floor'].shape[0]) & (gj >= 0) & (gj < F['floor'].shape[1])
        seen = np.zeros(F['floor'].shape, bool)
        seen[gi[ok], gj[ok]] = True
        c = float((seen & F['floor']).sum()) * F['res'] ** 2
        return free, c, 100.0 * c / F['m2']

    # ------------------------------------------------------------ sampling
    def active_path(self):
        if self.paths['plan_smoothed'] is not None and self.path_t['plan_smoothed'] >= self.path_t['plan'] - 1.0:
            return self.paths['plan_smoothed'], 'smoothed'
        return self.paths['plan'], 'raw'

    def tick(self):
        t = self.now()
        if t == self.last_sim:      # sim paused or no /clock yet
            return
        if self.last_sim is not None and t < self.last_sim - 1.0:
            self.reset(launch_log=self.launch_log)      # a new sim started (sim time went back)
            return
        self.last_sim = t
        self.last_sim_change = time.time()
        try:
            mb = self.buf.lookup_transform('map', 'base_footprint', Time())
        except Exception:
            return
        x, y = mb.transform.translation.x, mb.transform.translation.y
        yaw = yaw_q(mb.transform.rotation)
        vx, wz = self.odom
        cv, cw, ct = self.cmd
        if t - ct > 0.5:
            cv = cw = 0.0
        s = {'t': t, 'w': time.time(), 'x': x, 'y': y, 'yaw': yaw, 'vx': vx, 'wz': wz,
             'cv': cv, 'cw': cw, 'ctrl': self.ctrl, 'front': self.scan[0], 'width': self.scan[1],
             'xte': float('nan'), 'hdev': float('nan')}
        with self.lock:
            P, src = self.active_path()
            if P is not None and len(P) > 2:
                d = np.hypot(P[:, 0] - x, P[:, 1] - y)
                k = min(int(np.argmin(d)), len(P) - 2)
                tang = math.atan2(P[k + 1, 1] - P[k, 1], P[k + 1, 0] - P[k, 0])
                # driving backwards along the path is on-track, not 180 deg off
                h = wrap(yaw + (math.pi if vx < -0.01 else 0.0) - tang)
                s['xte'] = float(d.min())
                s['hdev'] = math.degrees(h)
            self.samples.append(s)

    # ------------------------------------------------------------ queries
    def state(self):
        with self.lock:
            s = self.samples[-1] if self.samples else None
            out = {'sim_time': round(self.now(), 1), 'pose': None}
            if s:
                out['pose'] = {k: _r(v) if isinstance(v, float) else v for k, v in s.items() if k != 'w'}
                out['pose']['yaw_deg'] = round(math.degrees(s['yaw']), 1)
            if self.goals:
                g = self.goals[-1]
                out['goal'] = {'x': round(g[1], 2), 'y': round(g[2], 2), 'set_at': round(g[0], 1),
                               'dist': round(math.hypot(g[1] - s['x'], g[2] - s['y']), 2) if s else None,
                               'count': len(self.goals)}
            if self.events:
                out['last_goal_event'] = {'t': round(self.events[-1][0], 1), 'kind': self.events[-1][1]}
            if self.cov:
                out['coverage'] = {'known_free_m2': round(self.cov[-1][1], 1),
                                   'floor_m2': round(self.cov[-1][2], 1), 'pct': round(self.cov[-1][3], 1)}
            elif self.map is not None:
                a = _grid(self.map)
                out['coverage'] = {'known_free_m2': round(float((a == 0).sum()) * self.map.info.resolution ** 2, 1)}
            out['controller'] = self.ctrl
            out['manual_override'] = self.override
            out['exploration_complete_at'] = self.complete_t
            if self.plans:
                p = self.plans[-1]
                out['last_plan'] = {'t': round(p[0], 1), 'len_m': round(p[1], 2),
                                    'unknown_share': _r(p[2]), 'lethal_share': _r(p[3])}
            out['hz'] = {t: round(self.hz(t), 1) for t in ('/scan', '/odom', '/cmd_vel_nav', '/map', '/plan')}
            out['subscribed'] = len(self.subs)
            return out

    def logs(self, min_level=30, node=None, grep=None, since=None, last=60):
        with self.lock:
            rows = [r for r in self.rosout if r[2] >= min_level
                    and (node is None or node in r[3])
                    and (grep is None or grep.lower() in r[4].lower())
                    and (since is None or r[0] >= since)]
        return rows[-last:]

    def _scan_launch_log(self):
        if not self.launch_log or not os.path.exists(self.launch_log):
            return
        with open(self.launch_log, errors='replace') as f:
            f.seek(self.log_off)
            new = f.read()
            self.log_off = f.tell()
        for l in new.splitlines():
            if 'process has died' in l or 'was required: shutting down' in l or 'symbol lookup error' in l:
                self.died.append((self.now(), re.sub(r'\x1b\[[0-9;]*m', '', l)[:220]))

    def health(self, launch_running=None):
        """Current alerts: [{'kind', 'msg'}]. Kinds in ALERTS_STOP mean 'look now'."""
        self._scan_launch_log()
        A = []
        wall = time.time()
        up = wall - self.reset_wall
        if launch_running is False:
            A.append({'kind': 'launch_exited', 'msg': 'the launch process has exited'})
        for t, l in self.died[-3:]:
            A.append({'kind': 'node_died', 'msg': l})
        if up > 20 and wall - self.last_sim_change > 8:
            A.append({'kind': 'no_clock', 'msg': f'sim time frozen for {wall - self.last_sim_change:.0f} s '
                                                 '(paused, crashed, or no /clock)'})
        with self.lock:
            S = list(self.samples)
        if up > 45 and (not S or wall - S[-1]['w'] > 8):
            A.append({'kind': 'no_pose', 'msg': 'no map->base_footprint TF (SLAM or EKF not running?)'})
        if up > 45 and (self.map_wall is None or wall - self.map_wall > 40):
            A.append({'kind': 'no_map', 'msg': 'no /map for 40 s (SLAM Toolbox down or not publishing)'})
        if not S:
            return A
        tnow = S[-1]['t']
        explored = self.complete_t is not None
        if self.first_plan_t is not None and not explored and not self.override:
            old = [s for s in S if s['t'] <= tnow - 60]
            if old and tnow - self.first_plan_t > 60:
                win = [s for s in S if s['t'] >= tnow - 60]
                net = math.hypot(win[-1]['x'] - win[0]['x'], win[-1]['y'] - win[0]['y'])
                path = sum(math.hypot(b['x'] - a['x'], b['y'] - a['y']) for a, b in zip(win, win[1:]))
                if path < 0.3:
                    A.append({'kind': 'not_moving', 'msg': f'moved {path:.2f} m in the last 60 s'})
                turned = math.degrees(sum(abs(wrap(b['yaw'] - a['yaw'])) for a, b in zip(win, win[1:])))
                if turned >= 300 and path < 1.0:
                    A.append({'kind': 'rotation', 'msg': f'turned {turned:.0f} deg in 60 s while driving {path:.2f} m '
                                                         f'({net:.2f} m net; rotation event)'})
            rtf_win = [s for s in S if s['w'] >= wall - 20]
            if len(rtf_win) > 20:
                rtf = (rtf_win[-1]['t'] - rtf_win[0]['t']) / max(rtf_win[-1]['w'] - rtf_win[0]['w'], 1e-6)
                if rtf < 0.4:
                    A.append({'kind': 'low_rtf', 'msg': f'real-time factor {rtf:.2f} (GPU offload? CPU load?)'})
            for topic, lo in MIN_HZ.items():
                if topic == '/cmd_vel_nav' and abs(S[-1]['cv']) + abs(S[-1]['cw']) < 1e-3:
                    continue
                h = self.hz(topic)
                if topic in self.subs and h < lo:
                    A.append({'kind': 'low_rate', 'msg': f'{topic} at {h:.1f} Hz (expected >= {lo})'})
        with self.lock:
            cov = list(self.cov)
        if cov and cov[-1][3] < 90 and cov[-1][0] - cov[0][0] > 180:
            old = [c for c in cov if c[0] <= cov[-1][0] - 180]
            if old and cov[-1][2] - old[-1][2] < 0.5:
                A.append({'kind': 'coverage_stalled', 'msg': f'< 0.5 m2 new floor in 180 s (at {cov[-1][3]:.1f} %)'})
        if explored:
            A.append({'kind': 'complete', 'msg': f'exploration complete at t={self.complete_t:.0f}s'})
        return A

    def summarize(self, t0, t1):
        """Tuning summary over the sim-time window [t0, t1]."""
        with self.lock:
            allS = list(self.samples)
            logs = [r for r in self.rosout if t0 <= r[0] <= t1 and r[2] >= 30]
            goals = [g for g in self.goals if t0 <= g[0] <= t1]
            events = [e for e in self.events if t0 <= e[0] <= t1]
            ctrl = [c for c in self.ctrl_log if t0 <= c[0] <= t1]
            plans = [p for p in self.plans if t0 <= p[0] <= t1]
            cov = [c for c in self.cov if c[0] <= t1]
            cov0 = [c for c in self.cov if c[0] <= t0]
        S = [s for s in allS if t0 <= s['t'] <= t1]
        out = {'window_sim_s': round(t1 - t0, 1), 'samples': len(S)}
        if len(S) >= 2:
            out.update(motion_metrics(allS, S, self.retrace_windows()))
        out['goals'] = {'new_best_goals': len(goals), **dict(collections.Counter(e[1] for e in events))}
        out['controller_switches'] = [(round(t, 1), c) for t, c in ctrl][:20]
        if plans:
            out['plans'] = {'count': len(plans), 'mean_len_m': round(float(np.mean([p[1] for p in plans])), 2),
                            'with_unknown_cells': int(sum(1 for p in plans if p[2] > 0)),
                            'with_lethal_cells': int(sum(1 for p in plans if p[3] > 0))}
        if cov:
            out['coverage_pct'] = {'start': round(cov0[-1][3], 1) if cov0 else 0.0, 'end': round(cov[-1][3], 1)}
            out['floor_gain_m2'] = round(cov[-1][2] - (cov0[-1][2] if cov0 else 0.0), 2)
        if logs:
            byn = collections.Counter(r[3] for r in logs)
            msgs = collections.Counter((LEVELS.get(r[2], r[2]), r[3], re.sub(r'[-\d.]+', '#', r[4][:160]))
                                       for r in logs)
            out['warn_error_by_node'] = dict(byn.most_common(10))
            out['top_messages'] = [f'{n}x [{lv}] {node}: {m}' for (lv, node, m), n in msgs.most_common(12)]
        if self.complete_t is not None and t0 <= self.complete_t <= t1:
            out['exploration_complete_at'] = round(self.complete_t, 1)
        return out

    def retrace_windows(self):
        """(start, end + 3 s) of every retrace: the robot follows its own track while Nav2's path is
        stale, so these samples are left out of xte/heading (nav-lessons: else 102 deg 'errors')."""
        with self.lock:
            ev = list(self.events)
        out, start = [], None
        for t, k, _ in ev:
            if k == 'retrace':
                start = t
            elif start is not None and k in ('retrace_end', 'sent', 'reached', 'gave_up'):
                out.append((start, t + 3.0))
                start = None
        if start is not None:
            out.append((start, float('inf')))
        return out

    def track_array(self):
        with self.lock:
            keys = ['t', 'w', 'x', 'y', 'yaw', 'vx', 'wz', 'cv', 'cw', 'front', 'width', 'xte', 'hdev']
            out = {k: np.array([s[k] for s in self.samples], float) for k in keys}
            out['ctrl'] = np.array([s['ctrl'] or '' for s in self.samples])
            out['cov'] = np.array(list(self.cov), float).reshape(-1, 4)
            out['plans'] = np.array(list(self.plans), float).reshape(-1, 4)
            # (t, points out of costmap bounds, unknown points inside, last point bad, first bad index,
            #  points, costmap age s, -1 points against the NEXT costmap (-1 = none arrived))
            out['plan_unknown_detail'] = np.array([r + (-1,) * (8 - len(r)) for r in self.plan_unknown_detail],
                                                  float).reshape(-1, 8)
            out['goal_events'] = np.array([f'{t:.1f}|{k}|{m}' for t, k, m in self.events])
            return out


def motion_metrics(allS, S, exclude=()):
    """Metrics over samples S (allS gives context for the +-30 s stuck window). exclude: sim-time
    windows left out of the tracking metrics (retraces)."""
    T = np.array([s['t'] for s in allS])
    XY = np.array([[s['x'], s['y']] for s in allS])
    t = np.array([s['t'] for s in S])
    xy = np.array([[s['x'], s['y']] for s in S])
    seg = np.r_[0, np.linalg.norm(np.diff(xy, axis=0), axis=1)]
    dt = np.r_[0, np.diff(t)]
    vx = np.array([s['vx'] for s in S]); wz = np.array([s['wz'] for s in S])
    cv = np.array([s['cv'] for s in S]); cw = np.array([s['cw'] for s in S])
    yaw = np.array([s['yaw'] for s in S])
    width = np.array([s['width'] for s in S]); xte = np.array([s['xte'] for s in S])
    hdev = np.abs(np.array([s['hdev'] for s in S]))
    dyaw = np.r_[0, np.abs(wrap(np.diff(yaw)))]
    # stuck: < 0.5 m net over the surrounding 60 s
    a = np.searchsorted(T, t - 30); b = np.clip(np.searchsorted(T, t + 30), 0, len(T) - 1)
    stuck = np.linalg.norm(XY[b] - XY[a], axis=1) < 0.5
    moving = (np.abs(vx) > 0.02) | (np.abs(wz) > 0.05)
    commanded = (np.abs(cv) > 0.03) | (np.abs(cw) > 0.1)
    wall = S[-1]['w'] - S[0]['w']
    total = max(dt.sum(), 1e-6)
    out = {
        'rtf': round((t[-1] - t[0]) / wall, 2) if wall > 0 else None,
        'distance_m': round(float(seg.sum()), 2),
        'net_displacement_m': round(float(np.linalg.norm(xy[-1] - xy[0])), 2),
        'reverse_m': round(float(seg[vx < -0.01].sum()), 2),
        'mean_speed': round(float(seg.sum() / total), 3),
        'time_budget_pct': {   # as budget.py
            'forward': round(100 * float(dt[vx > 0.05].sum()) / total, 1),
            'reverse': round(100 * float(dt[vx < -0.05].sum()) / total, 1),
            'turn_on_spot': round(100 * float(dt[(np.abs(vx) <= 0.03) & (np.abs(wz) > 0.15)].sum()) / total, 1),
            'creep': round(100 * float(dt[(np.abs(vx) > 0.03) & (np.abs(vx) <= 0.05)].sum()) / total, 1),
            'still': round(100 * float(dt[(np.abs(vx) <= 0.03) & (np.abs(wz) <= 0.15)].sum()) / total, 1)},
        'stuck_pct': round(100 * float(dt[stuck].sum()) / total, 1),
        'spin_in_place_deg': round(math.degrees(float(dyaw[np.abs(vx) < 0.03].sum())), 0),
        'commanded_not_moving_s': round(float(dt[commanded & ~moving].sum()), 1),
        'min_front_clearance_m': _r(np.nanmin([s['front'] for s in S])) if np.isfinite([s['front'] for s in S]).any() else None,
    }
    track = (vx > 0.05) & ~stuck & np.isfinite(xte)
    for a0, a1 in exclude:
        track &= ~((t >= a0) & (t <= a1))
    if exclude:
        out['retrace_s_excluded'] = round(float(sum(dt[(t >= a0) & (t <= a1)].sum() for a0, a1 in exclude)), 1)
    for name, sel in (('all', track), ('tunnel', track & (width < 1.2)), ('open', track & (width > 2.0))):
        if sel.sum() >= 5:
            large = (xte[sel] > 0.10) | (hdev[sel] > 30)
            out[f'tracking_{name}'] = {
                'n': int(sel.sum()), 'xte_mean': _r(xte[sel].mean()), 'xte_p95': _r(np.percentile(xte[sel], 95)),
                'hdev_mean': _r(hdev[sel].mean(), 1), 'hdev_p95': _r(np.percentile(hdev[sel], 95), 1),
                'large_dev_pct': round(100 * float(large.mean()), 1)}
    # rotation events: >= 300 deg of turning within 60 s while driving < 1 m (path length; non-overlapping).
    # rotation_events_net: the definition before 2026-10-21 (< 1 m net displacement), for comparisons.
    cum, cpath = np.cumsum(dyaw), np.cumsum(seg)
    for key, short in (('rotation_events', lambda i, j: cpath[j] - cpath[i] < 1.0),
                       ('rotation_events_net', lambda i, j: np.linalg.norm(xy[j] - xy[i]) < 1.0)):
        ev, i = [], 0
        while i < len(S):
            j = np.searchsorted(t, t[i] + 60, side='right') - 1
            if j > i and math.degrees(cum[j] - cum[i]) >= 300 and short(i, j):
                ev.append({'t': round(t[i], 1), 'x': round(xy[i, 0], 2), 'y': round(xy[i, 1], 2),
                           'width': _r(width[i], 2)})
                i = j + 1
            else:
                i += 1
        out[key] = {'count': len(ev), 'first': ev[:8]}
    # stall episodes: >= 3 s commanded but not moving
    stall = commanded & ~moving
    eps, st = [], None
    for k in range(len(S)):
        if stall[k] and st is None:
            st = k
        if (not stall[k] or k == len(S) - 1) and st is not None:
            if t[k] - t[st] >= 3.0:
                eps.append({'t': round(t[st], 1), 'dur_s': round(t[k] - t[st], 1),
                            'x': round(xy[st, 0], 2), 'y': round(xy[st, 1], 2), 'ctrl': S[st]['ctrl']})
            st = None
    out['stall_episodes'] = {'count': len(eps), 'first': eps[:10]}
    return out


def smoke_verdict(w, launch_running, min_move=1.5):
    """Gate after a change. Hard checks decide PASS/FAIL (does it run at all: spawned, map, Nav2
    planning, moving, nothing died). Warnings are quality signals to look at, not a failure
    (e.g. the known start-up U-turn of tunnel_reverse counts as a rotation event)."""
    with w.lock:
        S = list(w.samples)
        plans = list(w.plans)
    checks = {
        'launch alive': bool(launch_running),
        'pose (robot spawned, TF ok)': bool(S),
        '/map arriving': w.map is not None,
        'Nav2 planned a path': w.first_plan_t is not None,
        'no node died': not w.died,
    }
    warnings = {}
    dist = sum(math.hypot(b['x'] - a['x'], b['y'] - a['y']) for a, b in zip(S, S[1:])) if S else 0.0
    checks[f'drove >= {min_move} m (drove {dist:.2f})'] = dist >= min_move
    if len(S) > 10:
        m = motion_metrics(S, S)
        warnings['rotation events'] = m['rotation_events']
        warnings['large deviation % (all)'] = (m.get('tracking_all') or {}).get('large_dev_pct')
        warnings['stall episodes'] = m['stall_episodes']['count']
    warnings['plans through unknown'] = sum(1 for p in plans if p[2] > 0)
    return all(checks.values()), {'checks': checks, 'warnings': warnings}


# ---------------------------------------------------------------- rendering
def render(w=None, radius=None, last_s=None, costmap=True, width_px=1100, data=None, title_extra='',
           center=None):
    """Top-down map with track (green forward, red reverse, orange spin-in-place), plan, goal, robot.
    From a live watcher w, or from data=dict(map grid/res/origin, samples arrays) for saved runs."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    if data is None:
        with w.lock:
            m, c = w.map, (w.costmap if costmap else None)
            S = list(w.samples)
            P, Ps = w.paths['plan'], w.paths['plan_smoothed']
            goal = w.goals[-1] if w.goals else None
            cov = w.cov[-1] if w.cov else None
            now = w.now()
        if m is None:
            raise RuntimeError('no /map received yet')
        if last_s and S:
            S = [s for s in S if s['t'] >= S[-1]['t'] - last_s]
        g = _grid(m)
        res, ox, oy = m.info.resolution, m.info.origin.position.x, m.info.origin.position.y
        cg = None
        if c is not None:
            cg = (_grid(c).astype(float), c.info.resolution, c.info.origin.position.x, c.info.origin.position.y)
        tr = {k: np.array([s[k] for s in S]) for k in ('x', 'y', 'yaw', 'vx', 'wz')} if S else None
        ctrl = S[-1]['ctrl'] if S else None
    else:
        g, res, (ox, oy) = data['map'], float(data['map_res']), data['map_origin']
        cg, P, Ps, goal, ctrl = None, None, None, None, None
        tr = {k: data[k] for k in ('x', 'y', 'yaw', 'vx', 'wz')} if len(data['t']) else None
        cov = data['cov'][-1] if len(data.get('cov', [])) else None
        now = float(data['t'][-1]) if len(data['t']) else 0.0
    ext = [ox, ox + g.shape[1] * res, oy, oy + g.shape[0] * res]
    img = np.full(g.shape, 0.80)
    img[g == 0] = 1.0
    occ = g > 0
    img[occ] = 1.0 - np.clip(g[occ], 0, 100) / 100.0
    fig = plt.figure(figsize=(width_px / 100, width_px / 100), dpi=100)
    ax = fig.add_axes([0.06, 0.05, 0.92, 0.9])
    ax.imshow(img, cmap='gray', vmin=0, vmax=1, origin='lower', extent=ext, interpolation='nearest')
    if cg is not None:
        cv_, cres, cox, coy = cg
        ov = np.zeros(cv_.shape + (4,))
        infl = (cv_ > 0) & (cv_ < 99)
        ov[infl] = [1.0, 0.75, 0.0, 0.0]
        ov[infl, 3] = 0.12 + 0.3 * cv_[infl] / 99.0
        ov[cv_ >= 99] = [0.9, 0.1, 0.1, 0.55]
        ax.imshow(ov, origin='lower', interpolation='nearest',
                  extent=[cox, cox + cv_.shape[1] * cres, coy, coy + cv_.shape[0] * cres])
    if tr is not None and len(tr['x']) > 1:
        xy = np.c_[tr['x'], tr['y']]
        segs = np.stack([xy[:-1], xy[1:]], axis=1)
        cols = np.where(tr['vx'][1:, None] < -0.01, [[0.84, 0.15, 0.16, 1]], [[0.17, 0.63, 0.17, 1]])
        ax.add_collection(LineCollection(segs, colors=cols, linewidths=1.6, capstyle='round'))
        spin = (np.abs(tr['vx']) < 0.02) & (np.abs(tr['wz']) > 0.25)
        if spin.any():
            ax.scatter(xy[spin, 0], xy[spin, 1], s=6, color='#ff7f0e', zorder=4, label='spin in place')
        ax.plot([], [], color='#2ca02c', label='forward')
        ax.plot([], [], color='#d62728', label='reverse')
    if P is not None:
        ax.plot(P[:, 0], P[:, 1], color='#1f77b4', lw=1.2, label='/plan')
    if Ps is not None:
        ax.plot(Ps[:, 0], Ps[:, 1], color='#17becf', lw=1.2, ls='--', label='/plan_smoothed')
    if goal:
        ax.scatter([goal[1]], [goal[2]], marker='*', s=260, color='gold', edgecolor='k', zorder=6, label='goal')
    if tr is not None and len(tr['x']):
        x, y, yaw = tr['x'][-1], tr['y'][-1], tr['yaw'][-1]
        ax.add_patch(plt.Circle((x, y), ROBOT_R, fill=False, color='k', lw=1.2, zorder=7))
        ax.arrow(x, y, 0.35 * math.cos(yaw), 0.35 * math.sin(yaw), width=0.04,
                 color='k', zorder=8, length_includes_head=True)
    if radius and center is not None:
        ax.set_xlim(center[0] - radius, center[0] + radius)
        ax.set_ylim(center[1] - radius, center[1] + radius)
    elif radius and tr is not None and len(tr['x']):
        ax.set_xlim(tr['x'][-1] - radius, tr['x'][-1] + radius)
        ax.set_ylim(tr['y'][-1] - radius, tr['y'][-1] + radius)
    else:
        iy, ix = np.nonzero(g >= 0)
        if len(ix):
            ax.set_xlim(ox + ix.min() * res - 1, ox + ix.max() * res + 1)
            ax.set_ylim(oy + iy.min() * res - 1, oy + iy.max() * res + 1)
    ax.set_aspect('equal')
    ax.grid(alpha=0.25)
    title = f'sim t={now:.0f}s'
    if cov is not None:
        title += f'   floor coverage {cov[3]:.1f}% ({cov[2]:.1f} m2)'
    if tr is not None and len(tr['x']) and data is None:
        title += f"   ctrl={ctrl}   v={tr['vx'][-1]:.2f} w={tr['wz'][-1]:.2f}"
    ax.set_title(title + title_extra, fontsize=10)
    ax.legend(loc='upper right', fontsize=8, framealpha=0.8)
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    return buf.getvalue()


_watcher = None
_spin = None


def watcher():
    global _watcher, _spin
    if _watcher is None:
        if not rclpy.ok():
            rclpy.init()
        _watcher = Watcher()
        ex = SingleThreadedExecutor()
        ex.add_node(_watcher)

        def spin():
            try:
                ex.spin()
            except Exception:       # ExternalShutdownException at exit
                pass
        _spin = threading.Thread(target=spin, daemon=True)
        _spin.start()
    return _watcher


def shutdown():
    """Stop spinning before interpreter exit (else: 'terminate called without an active exception')."""
    if _watcher is not None and rclpy.ok():
        rclpy.shutdown()
        _spin.join(2.0)
