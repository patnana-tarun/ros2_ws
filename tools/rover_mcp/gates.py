#!/usr/bin/env python3
"""Gates table for full exploration runs (nav-speed task, 2026-10-21).

    gates.py RUN_OR_EXPERIMENT_DIR [...]

Per run (a folder with summary.json + track.npz): coverage at 17 and 25 min, time to 90 / 95 %,
rotation events (path driven < 1 m; in brackets the old net-displacement count), stall episodes, stuck_pct, large_dev_pct and xte_p95 / hdev_p95 (all / tunnel /
open), open-space reversing (track.npz: vx < -0.05 among samples with LiDAR width > 2.0 m, from the
first /plan on), plans through unknown cells (still unknown in the next costmap; in brackets the raw
count), and PASS/FAIL per Must gate. Reads only; the metric
definitions stay in rosview.py.
"""
import glob
import json
import math
import os
import sys

import numpy as np


def cov_at(curve, s):
    v = [pc for t, pc in curve if t <= s]
    return v[-1] if v else None


def t_to(curve, pct):
    return next((t for t, pc in curve if pc >= pct), None)


def rotation_events(tr, t0):
    """(path-driven count, net-displacement count): >= 300 deg of turning within 60 s while the robot
    drives < 1 m (definition since 2026-10-21) / ends < 1 m from where it started (before). Same as
    rosview.motion_metrics, recomputed from track.npz so older runs can be re-scored."""
    k = tr['t'] >= t0
    t, x, y, yaw = tr['t'][k], tr['x'][k], tr['y'][k], tr['yaw'][k]
    cum = np.cumsum(np.r_[0, np.abs(np.angle(np.exp(1j * np.diff(yaw))))])
    cpath = np.cumsum(np.r_[0, np.hypot(np.diff(x), np.diff(y))])
    out = []
    for short in (lambda i, j: cpath[j] - cpath[i] < 1.0, lambda i, j: math.hypot(x[j] - x[i], y[j] - y[i]) < 1.0):
        n, i = 0, 0
        while i < len(t):
            j = np.searchsorted(t, t[i] + 60, side='right') - 1
            if j > i and math.degrees(cum[j] - cum[i]) >= 300 and short(i, j):
                n += 1
                i = j + 1
            else:
                i += 1
        out.append(n)
    return out


def unknown_plans(tr, m):
    """(counted, raw): plans with points on unknown cells; counted = still unknown in the next costmap
    or no later costmap (definition since 2026-10-21, from plan_unknown_detail column 7). Runs recorded
    before that diagnostic existed fall back to the raw count."""
    raw = m['plans']['with_unknown_cells_raw'] if 'with_unknown_cells_raw' in m['plans'] else m['plans']['with_unknown_cells']
    d = tr['plan_unknown_detail'] if 'plan_unknown_detail' in tr.files else None
    if d is None or (len(d) and d.shape[1] < 8):
        return raw, raw
    return int((d[:, 7] != 0).sum()) if len(d) else 0, raw


def run_row(rd):
    s = json.load(open(os.path.join(rd, 'summary.json')))
    m, curve = s['metrics'], s['coverage_curve']
    tr = np.load(os.path.join(rd, 'track.npz'), allow_pickle=True)
    t0 = tr['t'][-1] - s['duration_s']
    k = tr['t'] >= t0
    open_ = k & (tr['width'] > 2.0)
    rev_open = 100.0 * float((open_ & (tr['vx'] < -0.05)).sum()) / max(1, int(open_.sum()))
    t90, t95 = t_to(curve, 90), t_to(curve, 95)
    r = {'run': os.path.basename(rd), 'stop': s['stop_reason'], 'min': round(s['duration_s'] / 60, 1),
         'final': s['final_coverage_pct'], 'cov17': cov_at(curve, 1020), 'cov25': cov_at(curve, 1500),
         't90_min': round(t90 / 60, 1) if t90 is not None else None,
         't95_min': round(t95 / 60, 1) if t95 is not None else None,
         'rot': rotation_events(tr, t0)[0], 'rot_net': rotation_events(tr, t0)[1],
         'stalls': m['stall_episodes']['count'],
         'stuck': m['stuck_pct'], 'rev_open': round(rev_open, 1),
         'still': m['time_budget_pct'].get('still')}
    r['unknown_plans'], r['unknown_plans_raw'] = unknown_plans(tr, m)
    for z in ('all', 'tunnel', 'open'):
        tz = m.get('tracking_' + z) or {}
        r[f'ld_{z}'], r[f'xte_{z}'], r[f'hdev_{z}'] = tz.get('large_dev_pct'), tz.get('xte_p95'), tz.get('hdev_p95')
    r['g_cov'] = r['cov25'] is not None and r['cov25'] >= 90.0
    r['g_rot'] = r['rot'] == 0
    r['g_rev'] = r['rev_open'] <= 3.0
    r['g_unk'] = r['unknown_plans'] == 0
    r['g_stretch'] = r['cov17'] is not None and r['cov17'] >= 95.0
    return r


def main():
    rows = []
    for a in sys.argv[1:]:
        dirs = [a] if os.path.exists(os.path.join(a, 'summary.json')) else \
            sorted(d for d in glob.glob(os.path.join(a, '*')) if os.path.exists(os.path.join(d, 'summary.json')) and '_void_' not in d)
        rows += [run_row(d) for d in dirs]
    pf = lambda b: 'PASS' if b else 'FAIL'
    hdr = ('run', 'stop', 'cov17', 'cov25', 't90', 't95', 'rot (net)', 'stalls', 'stuck%', 'ld% all/tun/open',
           'xte95 all/tun/open', 'hdev95 all/tun/open', 'rev_open%', 'unk (raw)', 'still%', 'Must cov/rot/rev/unk', 'stretch')
    print('| ' + ' | '.join(hdr) + ' |')
    print('|' + '---|' * len(hdr))
    for r in rows:
        f3 = lambda p: '/'.join('-' if r[f'{p}_{z}'] is None else f'{r[f"{p}_{z}"]:g}' for z in ('all', 'tunnel', 'open'))
        print('| ' + ' | '.join(str(x) for x in (
            r['run'], r['stop'], r['cov17'], r['cov25'], r['t90_min'], r['t95_min'], f"{r['rot']} ({r['rot_net']})", r['stalls'],
            r['stuck'], f3('ld'), f3('xte'), f3('hdev'), r['rev_open'], f"{r['unknown_plans']} ({r['unknown_plans_raw']})", r['still'],
            '/'.join(pf(r[g]) for g in ('g_cov', 'g_rot', 'g_rev', 'g_unk')), pf(r['g_stretch']))) + ' |')
    if '--json' in os.environ.get('GATES', ''):
        print(json.dumps(rows, indent=1))


if __name__ == '__main__':
    main()
