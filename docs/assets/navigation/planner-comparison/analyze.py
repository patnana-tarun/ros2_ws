#!/usr/bin/env python3
"""Summarise the NavFn vs Smac Lattice A/B into per-run rows and per-planner mean/sd."""
import json, re, sys, glob, os, math
import numpy as np

B = os.path.dirname(os.path.abspath(__file__)); DUR = 600.0
EV = {
    'goals_sent': r'\[explore_coordinator\]: Sending goal',
    'goals_reached': r'\[explore_coordinator\]: Reached goal',
    'goal_timeouts': r'\[explore_coordinator\]: Goal took too long',
    'goals_rejected': r'\[explore_coordinator\]: Goal rejected',
    'nav2_failed': r'\[explore_coordinator\]: .*(aborted|failed|gave up)',
    'progress_fail': r'\[controller_server\]: Failed to make progress',
    'ctrl_missed_rate': r'\[controller_server\]: Control loop missed its desired rate',
    'planner_over_50ms': r'\[planner_server\]: Planner loop missed its desired rate',
    'backup': r'\[behavior_server\]: Running backup',
    'spin': r'\[behavior_server\]: Running spin',
    'backup_failed': r'\[behavior_server\]: backup failed',
    'collision_ahead': r'Collision Ahead',
    'plan_fail': r'\[planner_server\]: GridBased plugin failed to plan',
}


def log_counts(path):
    lines = [re.sub(r'\x1b\[[0-9;]*m', '', l) for l in open(path, errors='ignore')]
    st = lambda l: float(re.search(r'\[(\d{10}\.\d+)\]', l).group(1)) if re.search(r'\[(\d{10}\.\d+)\]', l) else None
    t0 = next((st(l) for l in lines if re.search(EV['goals_sent'], l)), None)
    out = {k: 0 for k in EV}; samples = {}
    for l in lines:
        t = st(l)
        if t is None or t0 is None or not (t0 - 1 <= t <= t0 + DUR): continue
        for k, p in EV.items():
            if re.search(p, l):
                out[k] += 1; samples.setdefault(k, l.strip()[:160])
    pt = []
    for l in lines:
        t = st(l)
        m = re.search(r'Planner loop missed its desired rate of [0-9.]+ Hz. Current loop rate is ([0-9.]+) Hz', l)
        if m and t0 is not None and t0 - 1 <= t <= t0 + DUR: pt.append(1000 / float(m.group(1)))
    fg = set()
    for l in lines:
        t = st(l); m = re.search(r'failed to plan from .* to \(([-0-9.]+), ([-0-9.]+)\)', l)
        if m and t0 is not None and t0 - 1 <= t <= t0 + DUR: fg.add(m.groups())
    out['plan_fail_distinct_goals'] = len(fg)
    out['slow_plan_ms_p50'] = float(np.median(pt)) if pt else 0.0
    out['slow_plan_ms_max'] = float(max(pt)) if pt else 0.0
    return out, samples


def stalls(cmd):
    """Stall = controller publishing |vx|<0.02 m/s and |wz|<0.08 rad/s continuously for > 3 s."""
    if not cmd: return 0, 0.0, 0.0
    t = np.array([c[0] for c in cmd]); small = np.array([abs(c[1]) < 0.02 and abs(c[2]) < 0.08 for c in cmd])
    active = np.diff(t) < 0.3; act_time = float(np.diff(t)[active].sum())
    n = 0; tot = 0.0; i = 0
    while i < len(t):
        if small[i]:
            j = i
            while j + 1 < len(t) and small[j + 1] and t[j + 1] - t[j] < 0.3: j += 1
            if t[j] - t[i] > 3.0: n += 1; tot += t[j] - t[i]
            i = j + 1
        else: i += 1
    return n, tot, act_time


def area_at(area, T):
    a = [x for x in area if x[0] is not None and x[0] <= T]
    return a[-1][1] if a else 0.0


def run_row(tag):
    d = json.load(open(f'{B}/{tag}.json')); lc, smp = log_counts(f'{B}/{tag}.launch.log')
    P = d['plans']; xte = np.array([x[1] for x in d['xte']]) if d['xte'] else np.array([0.0])
    n_st, t_st, t_act = stalls(d['cmd'])
    valid = [p['prev_valid'] for p in P if 'prev_valid' in p]
    pair = tag.split('_')[1]; cpu = json.load(open(f'{B}/cpu_{pair}.json')).get(tag, {})
    r = {
        'run': tag,
        'area_2.5min': area_at(d['area'], 150), 'area_5min': area_at(d['area'], 300),
        'area_7.5min': area_at(d['area'], 450), 'area_10min': area_at(d['area'], 600),
        'distance_m': d['dist'],
        **lc,
        'stall_episodes': n_st, 'stall_time_s': t_st, 'stall_pct_of_active': 100 * t_st / max(t_act, 1),
        'plans_per_min': len(P) / (DUR / 60),
        'replaced_plan_invalid_pct': 100 * (1 - np.mean(valid)) if valid else float('nan'),
        'path_turn_deg_per_m': float(np.median([math.degrees(p['turn_per_m']) for p in P])),
        'path_kinks30_per_m': float(np.median([p['kinks30'] / max(p['len'], 0.1) for p in P])),
        'path_fp_touch_inscribed_pct': 100 * float(np.mean([p['fp_frac_ge99'] for p in P])),
        'path_fp_cost_ge50_pct': 100 * float(np.mean([p['fp_frac_ge50'] for p in P])),
        'plans_fp_hits_lethal_pct': 100 * float(np.mean([p['fp_max'] >= 100 for p in P])),
        'path_heading_poses_pct': 100 * float(np.mean([p['heading_poses'] for p in P])),
        'xte_p50_cm': 100 * float(np.percentile(xte, 50)), 'xte_p90_cm': 100 * float(np.percentile(xte, 90)),
        'xte_p99_cm': 100 * float(np.percentile(xte, 99)), 'xte_gt10cm_pct': 100 * float((xte > 0.10).mean()),
        'planner_cpu_s': cpu.get('planner_cpu'), 'controller_cpu_s': cpu.get('controller_cpu'),
        'planner_cpu_ms_per_plan': 1000 * cpu['planner_cpu'] / max(len(P), 1) if cpu.get('planner_cpu') else None,
    }
    return r, smp


def main():
    rows = []; samples = {}
    for f in sorted(glob.glob(f'{B}/*_[0-9].json')):
        tag = os.path.basename(f)[:-5]
        if tag.startswith('cpu'): continue
        r, s = run_row(tag); rows.append(r); samples[tag] = s
    json.dump({'rows': rows, 'samples': samples}, open(f'{B}/summary.json', 'w'), indent=1)
    keys = [k for k in rows[0] if k != 'run']
    print(f"{'metric':32s}" + ''.join(f'{r["run"]:>10s}' for r in rows))
    for k in keys:
        print(f'{k:32s}' + ''.join(f'{(r[k] if r[k] is not None else float("nan")):10.2f}' for r in rows))
    print()
    print(f"{'metric':32s}{'NavFn mean±sd':>20s}{'Smac mean±sd':>20s}{'change':>10s}")
    for k in keys:
        a = np.array([r[k] for r in rows if r['run'].startswith('navfn') and r[k] is not None], float)
        b = np.array([r[k] for r in rows if r['run'].startswith('smac') and r[k] is not None], float)
        ch = (b.mean() - a.mean()) / abs(a.mean()) * 100 if a.size and abs(a.mean()) > 1e-9 else float('nan')
        print(f'{k:32s}{a.mean():12.2f} ±{a.std(ddof=1) if a.size > 1 else 0:6.2f}{b.mean():12.2f} ±{b.std(ddof=1) if b.size > 1 else 0:6.2f}{ch:9.0f}%')


main()
