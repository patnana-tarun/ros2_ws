#!/usr/bin/env python3
"""Root-cause checks on the 9 full-comparison runs (2026-10-19).

1. Paths through space that is not free: each /plan point is looked up in that run's FINAL SLAM
   map (80-91 % of the cave known). A point on an unknown or occupied final-map cell means the
   planner routed through space that turned out not to be traversable.
2. Full rotations: windows where the robot turned >= 300 deg in total (|integral of wz|) while
   its net displacement stayed < 1.0 m, within 60 s. Each is matched with what happened around it.
3. Deviation in open areas vs tunnels: cross-track error and heading deviation, driving forward,
   not stuck, split by LiDAR corridor width (< 1.2 m tunnel, > 2.0 m open).
"""
import json, re, sys, glob, os, math
import numpy as np

D = sys.argv[1]
OUT = {}


def load_map(tag):
    z = np.load(f'{D}/{tag}_map.npz'); return z['data'], float(z['res']), float(z['ox']), float(z['oy'])


def cell(m, x, y):
    g, r, ox, oy = m; i = int((y - oy) / r); j = int((x - ox) / r)
    return g[i, j] if 0 <= i < g.shape[0] and 0 <= j < g.shape[1] else -1


def events(tag, w0, w1):
    ev = []
    for l in open(f'{D}/{tag}.launch.log', errors='ignore'):
        l = re.sub(r'\x1b\[[0-9;]*m', '', l); m = re.search(r'\[(\d{10}\.\d+)\]', l)
        if not m: continue
        t = float(m.group(1)) - w0
        if not 0 <= t <= w1: continue
        for k, pat in (('send', 'Sending goal'), ('reached', 'Reached goal'), ('gaveup', 'gave up on the goal'),
                       ('spin', 'Running spin'), ('backup', 'Running backup'), ('progress_fail', 'Failed to make progress'),
                       ('new_goal_bt', 'Begin navigating')):
            if pat in l: ev.append((t, k, l.strip()[-90:]))
    return ev


rows = []
for f in sorted(glob.glob(f'{D}/*_[0-9].json')):
    tag = os.path.basename(f)[:-5]; d = json.load(open(f)); m = load_map(tag); S = d['samples']
    t = np.array([s['t'] for s in S]); w = np.array([s['w'] for s in S]); x = np.array([s['x'] for s in S]); y = np.array([s['y'] for s in S])
    yaw = np.array([s['yaw'] for s in S]); wz = np.array([s['wz'] for s in S]); vx = np.array([s['vx'] for s in S])
    width = np.array([s['width'] if s['width'] == s['width'] else 9 for s in S])
    xte = np.array([s.get('xte', np.nan) for s in S]); hdev = np.array([abs(s['hdev']) if 'hdev' in s else np.nan for s in S])
    # 1. paths through not-free space (raw /plan only)
    P = [p for p in d['paths'] if p['src'] == 'plan' and p['t'] is not None]
    bad = []
    for p in P:
        pts = np.array(p['pts']); v = np.array([cell(m, a, b) for a, b in pts])
        nf = (v != 0)            # unknown (-1) or occupied (>0) in the final map
        # longest consecutive run of not-free points, in metres (points are 0.2 m apart)
        run = mx = 0
        for q in nf: run = run + 1 if q else 0; mx = max(mx, run)
        bad.append((p['t'], float(nf.mean()), 0.2 * mx, p['len']))
    bad = np.array(bad)
    # 2. rotation events
    dt = np.r_[np.diff(t), 0.1].clip(0, 0.5); rot = []
    i = 0
    while i < len(t):
        j = i; acc = 0.0
        while j < len(t) and t[j] - t[i] < 60:
            acc += wz[j] * dt[j]
            if abs(acc) >= math.radians(300) and math.hypot(x[j] - x[i], y[j] - y[i]) < 1.0:
                rot.append((t[i], t[j], math.degrees(acc), x[i], y[i], width[i])); break
            j += 1
        i = j + 1 if rot and rot[-1][0] == t[i] else i + 5
    ev = events(tag, d['wall_start'], d['wall_s'])
    rot_ctx = []
    for (ta, tb, deg, rx, ry, wd) in rot:
        wa = w[np.searchsorted(t, ta)]; wb = w[min(np.searchsorted(t, tb), len(w) - 1)]
        near = [e[1] for e in ev if wa - 15 <= e[0] <= wb + 2]
        # did the path flip just before / during the rotation? compare plan headings at the robot
        Pw = [p for p in P if ta - 20 <= p['t'] <= tb]
        unk = [b[1] for b in bad if ta - 20 <= b[0] <= tb]
        rot_ctx.append(dict(t=round(ta / 60, 2), dur=round(tb - ta, 1), deg=round(deg), at=(round(rx, 1), round(ry, 1)), width=round(wd, 2),
                            events=sorted(set(near)), plans_through_notfree=round(float(np.mean([u > 0.05 for u in unk])) if unk else 0, 2)))
    # 3. open vs tunnel deviation
    lo = np.searchsorted(t, t - 30); hi = np.clip(np.searchsorted(t, t + 30), 0, len(t) - 1)
    stuck = np.hypot(x[hi] - x[lo], y[hi] - y[lo]) < 0.5
    drive = (vx > 0.05) & ~stuck
    tun = drive & (width < 1.2); opn = drive & (width > 2.0)
    q = lambda a, k, p: float(np.nanpercentile(a[k], p)) if k.any() else float('nan')
    rows.append(dict(run=tag, plans=len(P), plans_notfree_pct=100 * float((bad[:, 1] > 0.05).mean()),
                     longest_notfree_m_p90=float(np.percentile(bad[:, 2], 90)), rotations=len(rot),
                     xte_open_p50=100 * q(xte, opn, 50), xte_open_p90=100 * q(xte, opn, 90), xte_tun_p50=100 * q(xte, tun, 50), xte_tun_p90=100 * q(xte, tun, 90),
                     hdev_open_p50=q(hdev, opn, 50), hdev_open_p90=q(hdev, opn, 90), hdev_tun_p50=q(hdev, tun, 50), hdev_tun_p90=q(hdev, tun, 90)))
    OUT[tag] = rot_ctx
keys = [k for k in rows[0] if k != 'run']
print(f"{'':26s}" + ''.join(f'{r["run"]:>10s}' for r in rows))
for k in keys: print(f'{k:26s}' + ''.join(f'{r[k]:10.1f}' for r in rows))
print('\nrotation events (>= 300 deg within 60 s while moving < 1 m):')
for tag, rc in OUT.items():
    for r in rc: print(f'  {tag:9s}', r)
json.dump({'rows': rows, 'rotations': OUT}, open(f'{D}/diagnose.json', 'w'), indent=1)
