#!/usr/bin/env python3
"""Before/after validation of the demo fixes (exp/tunnel-tracking, 2026-10-19).

Usage: validate.py <before dir (full_runs)> <after dir (demo_runs)>
Before: base / smooth / tuned runs of the full comparison. After: demo_N runs. Same protocol.

Thresholds (from the robot and the baseline, fixed before the after-runs finished):
- large deviation: cross-track error > 10 cm (half the robot's 0.22 m width: a corner then
  reaches the 0.11 m inscribed band of a wall the path keeps clear of) or heading error > 30 deg
- rotation event: >= 300 deg of turning within 60 s while moving < 1 m net
- open area: LiDAR left + right clearance > 2.0 m; tunnel: < 1.2 m; samples driving forward
  (vx > 0.05) and not stuck (net movement >= 0.5 m over the surrounding 60 s)
- path through not-free space: path point on a cell that is unknown or occupied in that
  run's final SLAM map (same proxy for before and after)
- command limits: MPPI vx in [-0.1, 0.2] m/s, |wz| <= 0.6 rad/s (nav2_params*.yaml)
"""
import json, re, sys, glob, os, math
import numpy as np

BEF, AFT = sys.argv[1:3]
ARMS = ['base', 'smooth', 'tuned', 'demo', 'demo2']
TUN = {'B-E top': [(5, 3), (8.2, 5.6), (11.5, 5.9), (14.5, 4.5)], 'C-F': [(10, -1), (12.8, -3.8), (15, -5.5)]}


def segd(p, a, b):
    ab = b - a; t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1); return np.linalg.norm(p - (a + t * ab))


def near_tunnel(x, y, pts):
    p = np.array([x, y]); v = [np.array(q, float) for q in pts]
    return min(segd(p, a, b) for a, b in zip(v[:-1], v[1:])) < 0.6


def run(dirn, tag):
    d = json.load(open(f'{dirn}/{tag}.json')); S = d['samples']; w0 = d['wall_start']
    z = np.load(f'{dirn}/{tag}_map.npz'); g = z['data']; r = float(z['res']); ox = float(z['ox']); oy = float(z['oy'])
    def nf(a, b):
        i = int((b - oy) / r); j = int((a - ox) / r)
        return (not (0 <= i < g.shape[0] and 0 <= j < g.shape[1])) or g[i, j] != 0
    t = np.array([s['t'] for s in S]); x = np.array([s['x'] for s in S]); y = np.array([s['y'] for s in S])
    vx = np.array([s['vx'] for s in S]); wz = np.array([s['wz'] for s in S])
    width = np.array([s['width'] if s['width'] == s['width'] else 9 for s in S])
    xte = np.array([s.get('xte', np.nan) for s in S]); hd = np.array([abs(s['hdev']) if 'hdev' in s else np.nan for s in S])
    lo = np.searchsorted(t, t - 30); hi = np.clip(np.searchsorted(t, t + 30), 0, len(t) - 1)
    stuck = np.hypot(x[hi] - x[lo], y[hi] - y[lo]) < 0.5
    drive = (vx > 0.05) & ~stuck; opn = drive & (width > 2.0); tun = drive & (width < 1.2)
    big = (xte > 0.10) | (hd > 30)
    # rotation events
    dt = np.r_[np.diff(t), 0.1].clip(0, 0.5); rot = 0; i = 0
    while i < len(t):
        j = i; acc = 0.0; hit = False
        while j < len(t) and t[j] - t[i] < 60:
            acc += wz[j] * dt[j]
            if abs(acc) >= math.radians(300) and math.hypot(x[j] - x[i], y[j] - y[i]) < 1.0: hit = True; break
            j += 1
        if hit: rot += 1; i = j + 1
        else: i += 5
    # startup turn: total turning until the robot has moved 0.5 m
    k0 = int(np.argmax(np.hypot(x - x[0], y - y[0]) > 0.5))
    start_turn = math.degrees(float(np.sum(np.abs(np.diff(np.unwrap(np.array([s['yaw'] for s in S[:k0 + 1]])))))))
    # paths through not-free space (final-map proxy) and at plan time (after-runs only)
    raw = [p for p in d['paths'] if p['src'] == 'plan']
    nfr = []
    for p in raw:
        v = [nf(a, b) for a, b in p['pts']]; cur = mx = 0
        for q in v: cur = cur + 1 if q else 0; mx = max(mx, cur)
        nfr.append(0.2 * mx)
    nfr = np.array(nfr)
    sp = [p['space'] for p in d['paths'] if p.get('space')]
    # events
    ev = {'reached': 0, 'failed': 0, 'backup': 0, 'spin': 0, 'progress_fail': 0, 'refused': 0}
    for l in open(f'{dirn}/{tag}.launch.log', errors='ignore'):
        l = re.sub(r'\x1b\[[0-9;]*m', '', l); m = re.search(r'\[(\d{10}\.\d+)\]', l)
        if not m or not (0 <= float(m.group(1)) - w0 <= d['wall_s']): continue
        for k, pat in (('reached', 'Reached goal'), ('failed', 'gave up on the goal'), ('backup', 'Running backup'), ('spin', 'Running spin'),
                       ('progress_fail', 'Failed to make progress'), ('refused', 'blacklisted, not sent')):
            if pat in l: ev[k] += 1
    dur = d['dur'] / 60; per10 = lambda n: 10 * n / max(dur, 0.1)
    cov = d['cov']
    res = {'run': tag, 'stop': d['stop_reason'], 'reached_90': int(any(q[2] >= 90 for q in cov)),
           'time_to_90_min': next((q[0] / 60 for q in cov if q[2] >= 90), float('nan')), 'final_cov_pct': cov[-1][2],
           'open_big_pct': 100 * float(big[opn].mean()), 'open_xte_p90_cm': 100 * float(np.nanpercentile(xte[opn], 90)),
           'open_hdev_p90': float(np.nanpercentile(hd[opn], 90)), 'tun_hdev_p90': float(np.nanpercentile(hd[tun], 90)),
           'tun_xte_p90_cm': 100 * float(np.nanpercentile(xte[tun], 90)),
           'rotations_300': rot, 'startup_turn_deg': start_turn, 'stuck_pct': 100 * float(stuck.mean()),
           'plans_notfree_2m_pct': 100 * float((nfr >= 2.0).mean()) if nfr.size else float('nan'), 'notfree_longest_m': float(nfr.max()) if nfr.size else float('nan'),
           'goal_success_pct': 100 * ev['reached'] / max(ev['reached'] + ev['failed'], 1), 'goals_reached': ev['reached'], 'goals_given_up': ev['failed'],
           'refused_by_precheck': ev['refused'], 'backup_per10': per10(ev['backup']), 'spin_per10': per10(ev['spin']),
           'progress_fail_per10': per10(ev['progress_fail'])}
    for name, pts in TUN.items():
        k = np.array([near_tunnel(a, b, pts) for a, b in zip(x, y)])
        dk = k & (vx > 0.05) & ~stuck
        res[f'{name} time_s'] = float(k.sum()) / 10; res[f'{name} stuck_pct'] = 100 * float(stuck[k].mean()) if k.any() else float('nan')
        res[f'{name} hdev_p90'] = float(np.nanpercentile(hd[dk], 90)) if dk.any() else float('nan')
    if sp:
        res['plantime_unknown_max_share'] = max(q['unknown_share'] for q in sp); res['plantime_unknown_longest_m'] = max(q['unknown_run_m'] for q in sp)
        res['plantime_blocked_max_share'] = max(q['blocked_share'] for q in sp)
    if any('m2o' in s for s in S):
        m = np.array([s['m2o'] for s in S if 'm2o' in s]); j = np.hypot(np.diff(m[:, 0]), np.diff(m[:, 1])); jy = np.degrees(np.abs(np.angle(np.exp(1j * np.diff(m[:, 2])))))
        res['m2o_jumps_gt5cm'] = int((j > 0.05).sum()); res['m2o_jump_max_cm'] = 100 * float(j.max()); res['m2o_yaw_jump_max_deg'] = float(jy.max())
    tr = [s for s in S if 'truth' in s]
    if tr:
        e = np.degrees(np.abs(np.angle(np.exp(1j * np.array([s['yaw'] - s['truth'][2] for s in tr])))))
        res['yaw_err_vs_truth_p50'] = float(np.median(e)); res['yaw_err_vs_truth_max'] = float(e.max())
    C = np.array([c[1:] for c in d['cmd']]) if d['cmd'] else np.zeros((1, 2))
    res['cmd_vx_max'] = float(C[:, 0].max()); res['cmd_vx_min'] = float(C[:, 0].min()); res['cmd_wz_absmax'] = float(np.abs(C[:, 1]).max())
    return res


R = []
for dirn in (BEF, AFT):
    for f in sorted(glob.glob(f'{dirn}/*_[0-9].json')):
        tag = os.path.basename(f)[:-5]
        if tag.rsplit('_', 1)[0] in ARMS: R.append(run(dirn, tag))
json.dump(R, open(f'{AFT}/validation.json', 'w'), indent=1)
keys = [k for k in R[0] if k not in ('run', 'stop')] + [k for k in R[-1] if k not in R[0]]
print(f"{'metric':32s}" + ''.join(f'{r["run"]:>9s}' for r in R))
print(f"{'stop':32s}" + ''.join(f'{r["stop"][:8]:>9s}' for r in R))
for k in keys: print(f'{k:32s}' + ''.join(f'{r.get(k, float("nan")):9.1f}' for r in R))
print(); print(f"{'metric (mean)':32s}" + ''.join(f'{a:>10s}' for a in ARMS))
for k in keys:
    row = []
    for a in ARMS:
        v = [r[k] for r in R if r['run'].rsplit('_', 1)[0] == a and k in r and r[k] == r[k]]
        row.append(f'{np.mean(v):10.2f}' if v else f'{"-":>10s}')
    print(f'{k:32s}' + ''.join(row))
