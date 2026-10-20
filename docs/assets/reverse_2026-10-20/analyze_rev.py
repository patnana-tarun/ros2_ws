#!/usr/bin/env python3
"""Analysis + figures for the full comparison (exp/tunnel-tracking, 2026-10-19).

Usage: analyze_full.py <run dir> <figure dir>
Run dir: <arm>_<n>.json, <arm>_<n>_map.npz, <arm>_<n>.launch.log from full_recorder.py.

Definitions (fixed before the runs finished):
- stuck sample: robot net displacement over the surrounding 60 s (t-30 .. t+30) < 0.5 m
- tunnel sample: LiDAR left + right clearance (+-90 deg) < 1.2 m
- tracking metrics use only tunnel samples that are not stuck, driving forward (vx > 0.05)
- heading deviation: |robot yaw - direction of the followed path at the nearest point|
- turn reversals: sign changes of yaw rate between |wz| > 0.1 rad/s episodes, per metre in tunnels
- time lost per failed goal: from 'Sending goal' to 'gave up' for goals that were given up
"""
import json, re, sys, os, glob, math, csv
import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap

D, F = sys.argv[1:3]; os.makedirs(F, exist_ok=True)
TUNNEL_W = 1.2; STUCK_WIN = 30.0; STUCK_R = 0.5
ARMS = [('refR', 'Kept version (track 0.34)', '#2a78d6'), ('rev38', 'Reverse-out (track 0.38)', '#1baf7a'), ('kturn38', 'Three-point turn (track 0.38)', '#eb6834')]
SHORT = {'refR': 'kept\n0.34', 'rev38': 'reverse\n0.38', 'kturn38': 'K-turn\n0.38'}
SURF, T1, T2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 9.5, 'axes.edgecolor': T2, 'axes.labelcolor': T2, 'xtick.color': T2,
                     'ytick.color': T2, 'axes.titlecolor': T1, 'legend.frameon': False})
DEV = LinearSegmentedColormap.from_list('dev', ['#86b6ef', '#3987e5', '#2a78d6', '#184f95', '#0d366b'])
STOP = {'reached_90': 'reached 90 %', 'stuck_after_most': 'stuck above 75 %', 'cap': '40 min cap'}


def events(log, wall_start, wall_end):
    ev = []; goal = None; sent = None
    for l in open(log, errors='ignore'):
        l = re.sub(r'\x1b\[[0-9;]*m', '', l); m = re.search(r'\[(\d{10}\.\d+)\]', l)
        if not m: continue
        t = float(m.group(1)) - wall_start
        if t < 0 or t > wall_end: continue
        if (g := re.search(r'Sending goal: \(([-0-9.]+), ([-0-9.]+)\)', l)): goal = (float(g[1]), float(g[2])); sent = t
        elif 'Reached goal' in l and goal: ev.append(('reached', t, goal, t - sent)); goal = None
        elif 'gave up on the goal' in l and goal: ev.append(('failed', t, goal, t - sent)); goal = None
        elif 'No progress: moved' in l: ev.append(('stall_giveup', t, None, None))
        elif 'Goal took too long' in l: ev.append(('timeout', t, None, None))
        elif '[behavior_server]: Running backup' in l: ev.append(('backup', t, None, None))
        elif '[behavior_server]: Running spin' in l: ev.append(('spin', t, None, None))
        elif '[controller_server]: Failed to make progress' in l: ev.append(('progress_fail', t, None, None))
    return ev


def run_metrics(tag):
    d = json.load(open(f'{D}/{tag}.json')); S = d['samples']
    t = np.array([s['t'] for s in S]); w = np.array([s['w'] for s in S])
    x = np.array([s['x'] for s in S]); y = np.array([s['y'] for s in S])
    vx = np.array([s['vx'] for s in S]); wz = np.array([s['wz'] for s in S])
    width = np.array([s['width'] if s['width'] == s['width'] else 9.0 for s in S])
    hdev = np.array([abs(s['hdev']) if 'hdev' in s else np.nan for s in S])
    xte = np.array([s.get('xte', np.nan) for s in S])
    # stuck: net displacement over a 60 s window centred on the sample
    lo = np.searchsorted(t, t - STUCK_WIN); hi = np.clip(np.searchsorted(t, t + STUCK_WIN), 0, len(t) - 1)
    stuck = np.hypot(x[hi] - x[lo], y[hi] - y[lo]) < STUCK_R
    tun = width < TUNNEL_W; fwd = vx > 0.05; drive = tun & fwd & ~stuck
    step = np.r_[np.hypot(np.diff(x), np.diff(y)), 0]; dt = np.r_[np.diff(t), 0.1].clip(0, 0.5)
    dist_t = float(step[tun & ~stuck].sum())
    sg = np.sign(wz[tun & ~stuck & (np.abs(wz) > 0.1)]); rev = int((np.diff(sg) != 0).sum()) if sg.size > 1 else 0
    ev = events(f'{D}/{tag}.launch.log', d['wall_start'], d['wall_s'])
    cov = d['cov']; dur = d['dur'] / 60
    cov_at = lambda T: max([q[2] for q in cov if q[0] <= T] or [0])
    lost = [e[3] for e in ev if e[0] == 'failed']
    per10 = lambda n: 10 * n / max(dur, 0.1)
    cnt = lambda k: sum(e[0] == k for e in ev)
    m = {
        'run': tag, 'stop': d['stop_reason'], 'duration_min': dur,
        'time_to_90_min': next((q[0] / 60 for q in cov if q[2] >= 90.0), float('nan')),
        'final_cov_pct': cov[-1][2] if cov else 0.0, 'cov_10min_pct': cov_at(600), 'cov_20min_pct': cov_at(1200),
        'cov_30min_pct': cov_at(1800), 'distance_m': float(step.sum()),
        'stuck_pct': 100 * float(stuck.mean()), 'tunnel_drive_m': dist_t,
        'hdev_tunnel_p50': float(np.nanmedian(hdev[drive])) if drive.any() else np.nan,
        'hdev_tunnel_p90': float(np.nanpercentile(hdev[drive], 90)) if drive.any() else np.nan,
        'turn_reversals_per_m_tunnel': rev / max(dist_t, 0.1),
        'yaw_deg_per_m_tunnel': math.degrees(float((np.abs(wz) * dt)[tun & ~stuck].sum())) / max(dist_t, 0.1),
        'xte_std_cm_tunnel': 100 * float(np.nanstd(xte[drive])) if drive.any() else np.nan,
        'goals_reached': cnt('reached'), 'goals_failed': cnt('failed'),
        'lost_per_failed_goal_s': float(np.median(lost)) if lost else np.nan,
        'stall_giveups': cnt('stall_giveup'), 'timeouts': cnt('timeout'),
        'progress_fail_per10': per10(cnt('progress_fail')), 'backup_per10': per10(cnt('backup')), 'spin_per10': per10(cnt('spin')),
        'rtf': d['dur'] / d['wall_s'],
    }
    return m, dict(d=d, t=t, w=w, x=x, y=y, hdev=hdev, tun=tun, stuck=stuck, ev=ev)


def draw_map(ax, tag):
    z = np.load(f'{D}/{tag}_map.npz'); g = z['data']; r = float(z['res']); ox, oy = float(z['ox']), float(z['oy'])
    img = np.full(g.shape + (3,), 0.62); img[g == 0] = 1.0; img[g >= 65] = 0.08
    ax.imshow(img, origin='lower', extent=[ox, ox + g.shape[1] * r, oy, oy + g.shape[0] * r], interpolation='nearest')
    return ox, oy, g.shape[1] * r, g.shape[0] * r


def pose_at(R, tw):
    k = int(np.clip(np.searchsorted(R['w'], tw), 0, len(R['w']) - 1)); return R['x'][k], R['y'][k]


def draw_events(ax, R, legend=True):
    sty = {'reached': dict(marker='o', s=60, c='#0ca30c'), 'failed': dict(marker='o', s=60, c='#d03b3b'),
           'backup': dict(marker='v', s=50, c='#eb6834'), 'spin': dict(marker='*', s=110, c='#e87ba4')}
    names = {'reached': 'goal reached', 'failed': 'goal given up', 'backup': 'BackUp recovery', 'spin': 'Spin recovery'}
    seen = set(); gi = 0
    for kind, tw, g, _ in R['ev']:
        if kind not in sty: continue
        if g is None: g = pose_at(R, tw)
        ax.scatter(*g, edgecolor='black', linewidth=0.7, zorder=5, label=None if kind in seen or not legend else names[kind], **sty[kind]); seen.add(kind)
        if kind in ('reached', 'failed'):
            gi += 1; ax.annotate(str(gi), g, xytext=(4, 3), textcoords='offset points', fontsize=7, color=T1, zorder=6)
    ax.scatter(R['x'][0], R['y'][0], marker='s', s=50, c='white', edgecolor='black', zorder=6, label='start' if legend else None)


def run_card(tag, R, m, out):
    """Trajectory over the final SLAM map (coloured by time, events marked) + the run's metrics."""
    fig = plt.figure(figsize=(14, 6.6), dpi=150); fig.patch.set_facecolor(SURF)
    ax = fig.add_axes([0.04, 0.08, 0.62, 0.82]); tx = fig.add_axes([0.70, 0.08, 0.28, 0.82]); tx.axis('off')
    draw_map(ax, tag)
    pts = np.c_[R['x'], R['y']]; seg = np.stack([pts[:-1], pts[1:]], 1)
    lc = LineCollection(seg, cmap='viridis', linewidth=2.2, zorder=3); lc.set_array(R['t'][:-1] / 60); ax.add_collection(lc)
    st = R['stuck']
    if st.any(): ax.scatter(R['x'][st][::10], R['y'][st][::10], s=6, c='#d03b3b', alpha=0.35, zorder=4, label='stuck (moved < 0.5 m in 60 s)')
    draw_events(ax, R)
    cb = fig.colorbar(lc, ax=ax, fraction=0.03, pad=0.01); cb.set_label('sim minutes')
    ax.set_aspect('equal'); ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)')
    ax.legend(loc='lower left', fontsize=7.5, facecolor='white', framealpha=0.85, frameon=True)
    arm = tag.rsplit('_', 1)[0]; name = next(n for a, n, _ in ARMS if a == arm)
    ax.set_title(f'{tag} · {name} · {STOP.get(m["stop"], m["stop"])} after {m["duration_min"]:.1f} min', loc='left', fontsize=11)
    f = lambda v, fmt: '—' if v != v else fmt.format(v)
    rows = [('Outcome', None), ('Stop reason', STOP.get(m['stop'], m['stop'])), ('Run length', f(m['duration_min'], '{:.1f} min')),
            ('Time to 90 %', f(m['time_to_90_min'], '{:.1f} min')), ('Final coverage', f(m['final_cov_pct'], '{:.1f} %')),
            ('Coverage at 10 / 20 min', f'{m["cov_10min_pct"]:.0f} / {m["cov_20min_pct"]:.0f} %'), ('Distance driven', f(m['distance_m'], '{:.0f} m')),
            ('Time stuck', f(m['stuck_pct'], '{:.0f} %')),
            ('Tunnel driving', None), ('Heading deviation, median', f(m['hdev_tunnel_p50'], '{:.1f}°')),
            ('Heading deviation, p90', f(m['hdev_tunnel_p90'], '{:.1f}°')), ('Turn reversals per m', f(m['turn_reversals_per_m_tunnel'], '{:.2f}')),
            ('Yaw turned per m', f(m['yaw_deg_per_m_tunnel'], '{:.0f}°/m')), ('Side-to-side wobble (sd)', f(m['xte_std_cm_tunnel'], '{:.1f} cm')),
            ('Goals and recoveries', None), ('Goals reached / given up', f'{m["goals_reached"]} / {m["goals_failed"]}'),
            ('Time lost per given-up goal', f(m['lost_per_failed_goal_s'], '{:.0f} s')), ('Stall give-ups / timeouts', f'{m["stall_giveups"]} / {m["timeouts"]}'),
            ('"Failed to make progress" /10 min', f(m['progress_fail_per10'], '{:.1f}')), ('BackUp / Spin per 10 min', f'{m["backup_per10"]:.1f} / {m["spin_per10"]:.1f}')]
    yy = 0.98
    for k, v in rows:
        if v is None:
            tx.text(0, yy, k, fontsize=10.5, color=T1, weight='bold', transform=tx.transAxes); yy -= 0.052; continue
        tx.text(0.02, yy, k, fontsize=9.5, color=T2, transform=tx.transAxes); tx.text(0.98, yy, v, fontsize=9.5, color=T1, ha='right', transform=tx.transAxes)
        tx.plot([0.02, 0.98], [yy - 0.012] * 2, color=GRID, lw=0.6, transform=tx.transAxes); yy -= 0.047
    fig.savefig(out, facecolor=SURF); plt.close(fig)


def deviation_figure(runs, out):
    fig, axs = plt.subplots(1, len(runs), figsize=(6.2 * len(runs), 5.4), dpi=150); fig.patch.set_facecolor(SURF)
    ext = [draw_map(ax, tag) for ax, (tag, _, _, _) in zip(axs, runs)]
    x0 = min(e[0] for e in ext); y0 = min(e[1] for e in ext); x1 = max(e[0] + e[2] for e in ext); y1 = max(e[1] + e[3] for e in ext)
    for ax, (tag, label, R, m) in zip(axs, runs):
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_facecolor('#9e9e9e')
        pts = np.c_[R['x'], R['y']]; seg = np.stack([pts[:-1], pts[1:]], 1)
        h = np.nan_to_num(R['hdev'][:-1], nan=0).clip(0, 60)
        lc = LineCollection(seg, cmap=DEV, linewidth=np.where(R['tun'][:-1], 3.2, 1.4), zorder=3); lc.set_array(h); lc.set_clim(0, 60); ax.add_collection(lc)
        ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f'{label}\nheading deviation in tunnels: median {m["hdev_tunnel_p50"]:.0f}°, p90 {m["hdev_tunnel_p90"]:.0f}°\n'
                     f'{m["turn_reversals_per_m_tunnel"]:.2f} turn reversals per m · {STOP.get(m["stop"], m["stop"])}, {m["duration_min"]:.0f} min', loc='left', fontsize=9.5)
    cb = fig.colorbar(lc, ax=axs, fraction=0.015, pad=0.03); cb.set_label('heading deviation from path (°)')
    fig.suptitle('Heading deviation along the driven path (thick = inside a tunnel)', x=0.01, ha='left', fontsize=11.5, color=T1)
    fig.savefig(out, facecolor=SURF, bbox_inches='tight'); plt.close(fig)


def bars(M, keys, title, out, ncol=3):
    n = len(keys); nr = math.ceil(n / ncol)
    fig, axs = plt.subplots(nr, ncol, figsize=(3.8 * ncol, 3.3 * nr), dpi=150); fig.patch.set_facecolor(SURF)
    for ax in np.atleast_1d(axs).flat[n:]: ax.axis('off')
    for ax, (k, ttl) in zip(np.atleast_1d(axs).flat, keys):
        ax.set_facecolor(SURF); [ax.spines[s].set_visible(False) for s in ('top', 'right')]; ax.grid(axis='y', color=GRID, lw=0.8); ax.set_axisbelow(True)
        for x, (a, name, c) in enumerate(ARMS):
            v = [r[k] for r in M if r['run'].rsplit('_', 1)[0] == a and r[k] == r[k]]
            if not v: continue
            mean = float(np.mean(v)); ax.bar(x, mean, 0.6, color=c, zorder=2, alpha=0.9)
            ax.scatter(x + 0.17 + np.linspace(0, 0.1, len(v)), v, s=24, color='white', edgecolor=T1, linewidth=0.9, zorder=4)
            ax.annotate(f'{mean:.2f}' if mean < 1 else f'{mean:.1f}', (x - 0.08, mean), xytext=(0, 4), textcoords='offset points', ha='center', fontsize=8.5, color=T1)
        ax.set_xticks(range(len(ARMS))); ax.set_xticklabels([SHORT[a] for a, _, _ in ARMS], fontsize=8); ax.set_title(ttl, loc='left', fontsize=9.5); ax.set_ylim(0, None)
    fig.suptitle(title, x=0.01, ha='left', fontsize=11.5, color=T1)
    fig.tight_layout(); fig.savefig(out, facecolor=SURF); plt.close(fig)


def coverage_figure(RR, out):
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    [ax.spines[s].set_visible(False) for s in ('top', 'right')]; ax.grid(axis='y', color=GRID, lw=0.8)
    for a, name, c in ARMS:
        for i, (tag, R) in enumerate((k, v) for k, v in RR.items() if k.rsplit('_', 1)[0] == a):
            cv = R['d']['cov']; ax.step([q[0] / 60 for q in cv], [q[2] for q in cv], where='post', color=c, lw=1.8, alpha=0.9, label=name if i == 0 else None)
            ax.scatter(cv[-1][0] / 60, cv[-1][2], s=22, color=c, edgecolor=T1, linewidth=0.6, zorder=4)
    ax.axhline(90, color=T2, lw=1, ls='--'); ax.annotate('90 % target', (0.2, 90), xytext=(0, 4), textcoords='offset points', fontsize=8, color=T2)
    ax.axhline(75, color=GRID, lw=1, ls=':'); ax.annotate('75 %: "stuck" can end a run above this', (0.2, 75), xytext=(0, 4), textcoords='offset points', fontsize=7.5, color=T2)
    ax.set_xlabel('time since first plan (min)'); ax.set_ylabel('coverage of the cave floor (%)'); ax.set_ylim(0, 100); ax.set_xlim(0, max(R['d']['dur'] for R in RR.values()) / 60 + 1)
    ax.legend(loc='lower right'); ax.set_title('Coverage over time, every run (dot = where the run stopped)', loc='left', fontsize=11)
    fig.tight_layout(); fig.savefig(out, facecolor=SURF); plt.close(fig)


def trap_map(RR, out):
    """All stuck episodes of all runs on one map: where the cave traps the robot."""
    tag0 = max(RR, key=lambda k: RR[k]['d']['cov'][-1][2] if RR[k]['d']['cov'] else 0)
    fig, ax = plt.subplots(figsize=(11, 6.4), dpi=150); fig.patch.set_facecolor(SURF); draw_map(ax, tag0)
    for a, name, c in ARMS:
        first = True
        for tag, R in RR.items():
            if tag.rsplit('_', 1)[0] != a: continue
            st = R['stuck']
            if not st.any(): continue
            k = np.flatnonzero(st); br = np.flatnonzero(np.diff(k) > 1)
            for seg in np.split(k, br + 1):
                mins = len(seg) / 600
                if mins < 0.5: continue
                ax.scatter(R['x'][seg].mean(), R['y'][seg].mean(), s=40 + 60 * mins, color=c, alpha=0.75, edgecolor=T1, linewidth=0.6, zorder=4,
                           label=name if first else None); first = False
    ax.set_aspect('equal'); ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)')
    ax.legend(loc='lower left', fontsize=8.5, facecolor='white', framealpha=0.85, frameon=True)
    ax.set_title('Where the robot got stuck, all runs (circle area = minutes stuck; map from the most complete run)', loc='left', fontsize=10.5)
    fig.tight_layout(); fig.savefig(out, facecolor=SURF); plt.close(fig)


tags = sorted(os.path.basename(f)[:-5] for f in glob.glob(f'{D}/*_[0-9].json'))
M = []; RR = {}
for tag in tags:
    m, R = run_metrics(tag); M.append(m); RR[tag] = R
    run_card(tag, R, m, f'{F}/rev_card_{tag}.png')
json.dump(M, open(f'{D}/rev_summary.json', 'w'), indent=1)
with open(f'{D}/rev_summary.csv', 'w', newline='') as fh:
    wr = csv.DictWriter(fh, fieldnames=list(M[0])); wr.writeheader(); wr.writerows(M)
keys = [k for k in M[0] if k not in ('run', 'stop')]
print(f"{'metric':30s}" + ''.join(f'{r["run"]:>10s}' for r in M))
print(f"{'stop':30s}" + ''.join(f'{r["stop"][:9]:>10s}' for r in M))
for k in keys: print(f'{k:30s}' + ''.join(f'{r[k]:10.2f}' for r in M))
print(); print(f"{'metric (mean)':30s}" + ''.join(f'{a:>10s}' for a, _, _ in ARMS))
for k in keys:
    row = []
    for a, _, _ in ARMS:
        v = [r[k] for r in M if r['run'].rsplit('_', 1)[0] == a and r[k] == r[k]]
        row.append(f'{np.mean(v):10.2f}' if v else f'{"-":>10s}')
    print(f'{k:30s}' + ''.join(row))
if len(M) > 2:
    bars(M, [('hdev_tunnel_p50', 'Heading deviation in tunnels, median (°)'), ('hdev_tunnel_p90', 'Heading deviation in tunnels, p90 (°)'),
             ('turn_reversals_per_m_tunnel', 'Turn reversals per m in tunnels'), ('yaw_deg_per_m_tunnel', 'Yaw turned per m in tunnels (°/m)'),
             ('xte_std_cm_tunnel', 'Side-to-side wobble in tunnels (cm)'), ('stuck_pct', 'Time stuck (%)')],
         'Tunnel driving (stuck time left out): bars = mean, dots = runs', f'{F}/rev_tracking.png')
    bars(M, [('time_to_90_min', 'Time to 90 % (min; runs that got there)'), ('final_cov_pct', 'Coverage when the run ended (%)'),
             ('cov_20min_pct', 'Coverage at 20 min (%)'), ('lost_per_failed_goal_s', 'Time lost per given-up goal (s)'),
             ('progress_fail_per10', '"Failed to make progress" per 10 min'), ('backup_per10', 'BackUp per 10 min')],
         'Exploration outcome: bars = mean, dots = runs', f'{F}/rev_outcome.png')
    coverage_figure(RR, f'{F}/rev_coverage.png'); trap_map(RR, f'{F}/rev_traps.png')
    for n in sorted({t.rsplit('_', 1)[1] for t in tags}):
        runs = [(f'{a}_{n}', name, RR[f'{a}_{n}'], next(r for r in M if r['run'] == f'{a}_{n}')) for a, name, _ in ARMS if f'{a}_{n}' in RR]
        if len(runs) > 1: deviation_figure(runs, f'{F}/rev_deviation_round{n}.png')
