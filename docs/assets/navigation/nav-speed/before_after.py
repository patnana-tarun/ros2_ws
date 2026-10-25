#!/usr/bin/env python3
"""Before/after table for docs/issues/Nav speed 2026-10-21.md: the same p90 tracking metrics as
validate.py (tunnel-reverse 2026-10-20) computed from the rover MCP's track.npz files.

    before_after.py RUN_DIR [...]       (run folders with track.npz; summary.json optional)
"""
import json, os, sys
import numpy as np

def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi

def metrics(rd):
    d = np.load(os.path.join(rd, 'track.npz'), allow_pickle=True)
    t = d['t']
    s = json.load(open(os.path.join(rd, 'summary.json'))) if os.path.exists(os.path.join(rd, 'summary.json')) else None
    t0 = t[-1] - s['duration_s'] if s and 'duration_s' in s else next(float(e.split('|')[0]) for e in d['goal_events'] if '|sent|' in e)
    xy = np.c_[d['x'], d['y']]
    a = np.searchsorted(t, t - 30); b = np.clip(np.searchsorted(t, t + 30), 0, len(t) - 1)
    stuck = np.linalg.norm(xy[b] - xy[a], axis=1) < 0.5
    k = t >= t0
    ev = [(float(e.split('|')[0]), e.split('|')[1]) for e in d['goal_events']]
    excl, st = np.zeros(len(t), bool), None
    for tt, kk in ev:                                   # retrace windows (+3 s), as rosview
        if kk == 'retrace': st = tt
        elif st is not None and kk in ('retrace_end', 'sent', 'reached', 'gave_up'):
            excl |= (t >= st) & (t <= tt + 3); st = None
    track = k & (d['vx'] > 0.05) & ~stuck & np.isfinite(d['xte']) & ~excl
    hd = np.abs(d['hdev'])
    op, tu = track & (d['width'] > 2.0), track & (d['width'] < 1.2)
    cov = d['cov']; cov = cov[cov[:, 0] >= t0]
    t90 = next((c[0] - t0 for c in cov if c[3] >= 90), None)
    t95 = next((c[0] - t0 for c in cov if c[3] >= 95), None)
    dt = np.r_[0, np.diff(t)]
    sent = sum(1 for _, kk in ev if kk == 'sent'); reached = sum(1 for _, kk in ev if kk == 'reached')
    openk = k & (d['width'] > 2.0)
    yaw = np.unwrap(d['yaw']); dy = np.abs(np.diff(yaw, prepend=yaw[0])); cum = np.cumsum(dy)
    rot, i = 0, np.searchsorted(t, t0)
    while i < len(t):
        j = np.searchsorted(t, t[i] + 60, side='right') - 1
        if j > i and np.degrees(cum[j] - cum[i]) >= 300 and np.linalg.norm(xy[j] - xy[i]) < 1.0:
            rot += 1; i = j + 1
        else:
            i += 1
    return {
        'time_to_90_min': round(t90 / 60, 1) if t90 is not None else None,
        'time_to_95_min': round(t95 / 60, 1) if t95 is not None else None,
        'final_cov_pct': round(float(cov[-1][3]), 1),
        'open_big_pct': round(100 * float(((d['xte'][op] > 0.10) | (hd[op] > 30)).mean()), 1),
        'open_xte_p90_cm': round(100 * float(np.percentile(d['xte'][op], 90)), 1),
        'open_hdev_p90': round(float(np.percentile(hd[op], 90)), 1),
        'tun_xte_p90_cm': round(100 * float(np.percentile(d['xte'][tu], 90)), 1),
        'tun_hdev_p90': round(float(np.percentile(hd[tu], 90)), 1),
        'rotations_300': rot,
        'rotations_300_net': rot_net,
        'stuck_pct': round(100 * float(dt[k & stuck].sum() / dt[k].sum()), 1),
        'goal_success_pct': round(100 * reached / max(sent, 1), 1),
        'open_reverse_pct': round(100 * float((openk & (d['vx'] < -0.05)).sum() / max(openk.sum(), 1)), 1),
    }

rows = {os.path.basename(os.path.normpath(r)) + '@' + os.path.basename(os.path.dirname(os.path.normpath(r)))[-12:]: metrics(r) for r in sys.argv[1:]}
keys = list(next(iter(rows.values())))
print('| metric | ' + ' | '.join(rows) + ' |'); print('|---' * (len(rows) + 1) + '|')
for kk in keys:
    print(f'| {kk} | ' + ' | '.join('-' if r[kk] is None else str(r[kk]) for r in rows.values()) + ' |')
