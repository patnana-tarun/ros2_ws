#!/usr/bin/env python3
"""Analysis + figures for the tunnel-tracking GUI runs (exp/tunnel-tracking, 2026-10-18).

Usage: analyze_tunnel.py <run dir> <figure dir>
Run dir holds <arm>_<n>.json, <arm>_<n>_map.npz, <arm>_<n>.launch.log from tunnel_recorder.py.

Definitions (fixed before the runs):
- tunnel sample: LiDAR left + right clearance (+-90 deg, min over +-10 deg) < TUNNEL_W
- heading deviation: |robot yaw - tangent of the followed path at the nearest point|, only while
  driving forward (vx > 0.05 m/s)
- turn reversals: sign changes of odometry yaw rate between |wz| > 0.1 rad/s episodes
- yaw per metre: integral of |wz| dt / distance driven, both inside tunnels
"""
import json, re, sys, os, glob, math
import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap

D, F = sys.argv[1:3]; os.makedirs(F, exist_ok=True)
TUNNEL_W = 1.2; DUR = 600.0
ARMS = [('base', 'NavFn (current)', '#2a78d6'), ('smooth', 'NavFn + path smoothing', '#eb6834'),
        ('tuned', 'NavFn + smoothing + MPPI tuning', '#1baf7a')]
SURF, T1, T2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 9.5, 'axes.edgecolor': T2, 'axes.labelcolor': T2, 'xtick.color': T2,
                     'ytick.color': T2, 'axes.titlecolor': T1, 'legend.frameon': False})
# sequential ramp (one hue, light -> dark) for heading deviation
DEV = LinearSegmentedColormap.from_list('dev', ['#86b6ef', '#3987e5', '#2a78d6', '#184f95', '#0d366b'])  # starts at step 250: visible on white


def events(log, wall_start):
    """Goal / recovery / stall-related events from the launch log, as wall seconds since recorder start."""
    ev = []; goal = None
    for l in open(log, errors='ignore'):
        l = re.sub(r'\x1b\[[0-9;]*m', '', l); m = re.search(r'\[(\d{10}\.\d+)\]', l)
        if not m: continue
        t = float(m.group(1)) - wall_start
        if (g := re.search(r'Sending goal: \(([-0-9.]+), ([-0-9.]+)\)', l)): goal = (float(g[1]), float(g[2]))
        elif 'Reached goal' in l and goal: ev.append(('reached', t, goal)); goal = None
        elif 'gave up on the goal' in l and goal: ev.append(('failed', t, goal)); goal = None
        elif 'No path to frontier' in l and (g := re.search(r'\(([-0-9.]+), ([-0-9.]+)\)', l)):
            ev.append(('refused', t, (float(g[1]), float(g[2]))))
        elif '[behavior_server]: Running backup' in l: ev.append(('backup', t, None))
        elif '[behavior_server]: Running spin' in l: ev.append(('spin', t, None))
        elif '[controller_server]: Failed to make progress' in l: ev.append(('progress_fail', t, None))
    return ev


def run_metrics(tag):
    d = json.load(open(f'{D}/{tag}.json')); S = d['samples']
    t = np.array([s['t'] for s in S]); w = np.array([s['w'] for s in S])
    x = np.array([s['x'] for s in S]); y = np.array([s['y'] for s in S])
    vx = np.array([s['vx'] for s in S]); wz = np.array([s['wz'] for s in S])
    width = np.array([s['width'] if s['width'] == s['width'] else 9.0 for s in S])
    hdev = np.array([abs(s['hdev']) if 'hdev' in s else np.nan for s in S])
    xte = np.array([s.get('xte', np.nan) for s in S])
    tun = width < TUNNEL_W; fwd = vx > 0.05; dt = np.r_[np.diff(t), 0.1].clip(0, 0.5)
    step = np.r_[np.hypot(np.diff(x), np.diff(y)), 0]
    def revs(mask):
        sg = np.sign(wz[mask & (np.abs(wz) > 0.1)]); return int((np.diff(sg) != 0).sum()) if sg.size > 1 else 0
    dist_t = float(step[tun].sum())
    ev = events(f'{D}/{tag}.launch.log', d['wall_start'])
    a = [v for tt, v in d['area'] if tt is not None]
    area_at = lambda T: max([v for tt, v in d['area'] if tt is not None and tt <= T] or [0])
    m = {
        'run': tag, 'area_5min': area_at(300), 'area_10min': area_at(DUR), 'distance_m': float(step.sum()),
        'tunnel_share_pct': 100 * float(tun.mean()), 'tunnel_dist_m': dist_t,
        'hdev_tunnel_p50': float(np.nanmedian(hdev[tun & fwd])) if (tun & fwd).any() else np.nan,
        'hdev_tunnel_p90': float(np.nanpercentile(hdev[tun & fwd], 90)) if (tun & fwd).any() else np.nan,
        'hdev_all_p50': float(np.nanmedian(hdev[fwd])),
        'turn_reversals_per_m_tunnel': revs(tun) / max(dist_t, 0.1),
        'yaw_deg_per_m_tunnel': math.degrees(float((np.abs(wz) * dt)[tun].sum())) / max(dist_t, 0.1),
        'xte_std_cm_tunnel': 100 * float(np.nanstd(xte[tun & fwd])) if (tun & fwd).any() else np.nan,
        'goals_reached': sum(e[0] == 'reached' for e in ev), 'goals_failed': sum(e[0] == 'failed' for e in ev),
        'progress_fail': sum(e[0] == 'progress_fail' for e in ev),
        'backup': sum(e[0] == 'backup' for e in ev), 'spin': sum(e[0] == 'spin' for e in ev),
        'path_kinks_per_m': float(np.mean([p['kinks30_per_m'] for p in d['paths'] if p['src'] == ('plan_smoothed' if any(q['src'] == 'plan_smoothed' for q in d['paths']) else 'plan')])),
        'rtf': d['dur'] / d['wall_s'],
    }
    return m, dict(d=d, t=t, w=w, x=x, y=y, hdev=hdev, tun=tun, ev=ev)


def draw_map(ax, tag):
    z = np.load(f'{D}/{tag}_map.npz'); g = z['data']; r = float(z['res']); ox, oy = float(z['ox']), float(z['oy'])
    img = np.full(g.shape + (3,), 0.62); img[g == 0] = 1.0; img[g >= 65] = 0.08
    ax.imshow(img, origin='lower', extent=[ox, ox + g.shape[1] * r, oy, oy + g.shape[0] * r], interpolation='nearest')
    return ox, oy, g.shape[1] * r, g.shape[0] * r


def pose_at(R, tw):
    k = int(np.clip(np.searchsorted(R['w'], tw), 0, len(R['w']) - 1)); return R['x'][k], R['y'][k]


def trajectory_figure(tag, R, m, out):
    """run2_trajectory style: path over the final SLAM map, coloured by time, with events."""
    fig, ax = plt.subplots(figsize=(11, 6.4), dpi=150); fig.patch.set_facecolor(SURF)
    draw_map(ax, tag)
    pts = np.c_[R['x'], R['y']]; seg = np.stack([pts[:-1], pts[1:]], 1)
    lc = LineCollection(seg, cmap='viridis', linewidth=2.2, zorder=3); lc.set_array(R['t'][:-1] / 60); ax.add_collection(lc)
    cb = fig.colorbar(lc, ax=ax, fraction=0.025, pad=0.01); cb.set_label('sim minutes')
    sty = {'reached': dict(marker='o', s=70, c='#0ca30c'), 'failed': dict(marker='o', s=70, c='#d03b3b'),
           'refused': dict(marker='X', s=70, c='#d03b3b'), 'backup': dict(marker='v', s=60, c='#eb6834'),
           'spin': dict(marker='*', s=130, c='#e87ba4')}
    seen = set(); gi = 0
    for kind, tw, g in R['ev']:
        if kind not in sty: continue
        if g is None: g = pose_at(R, tw)
        ax.scatter(*g, edgecolor='black', linewidth=0.8, zorder=5, label=None if kind in seen else
                   {'reached': 'goal reached', 'failed': 'goal failed / timed out', 'refused': 'goal refused by pre-check',
                    'backup': 'BackUp recovery', 'spin': 'Spin recovery'}[kind], **sty[kind]); seen.add(kind)
        if kind in ('reached', 'failed'):
            gi += 1; ax.annotate(str(gi), g, xytext=(5, 4), textcoords='offset points', fontsize=7.5, color=T1, zorder=6)
    ax.scatter(R['x'][0], R['y'][0], marker='s', s=60, c='white', edgecolor='black', zorder=6, label='start')
    ax.set_aspect('equal'); ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)')
    ax.legend(loc='lower left', fontsize=8, facecolor='white', framealpha=0.85, frameon=True)
    ax.set_title(f'{tag}: {m["area_10min"]:.1f} m² explored in 10 min · goals reached {m["goals_reached"]}, failed {m["goals_failed"]}\n'
                 f'BackUp {m["backup"]} · Spin {m["spin"]} · heading deviation in tunnels: median {m["hdev_tunnel_p50"]:.0f}°',
                 loc='left', fontsize=10)
    fig.tight_layout(); fig.savefig(out, facecolor=SURF); plt.close(fig)


def deviation_figure(runs, out):
    """Side by side, one run per arm: path coloured by heading deviation (tunnel segments bold)."""
    fig, axs = plt.subplots(1, len(runs), figsize=(6.2 * len(runs), 5.2), dpi=150); fig.patch.set_facecolor(SURF)
    ext = [draw_map(ax, tag) for ax, (tag, _, _, _) in zip(np.atleast_1d(axs), runs)]
    x0 = min(e[0] for e in ext); y0 = min(e[1] for e in ext)
    x1 = max(e[0] + e[2] for e in ext); y1 = max(e[1] + e[3] for e in ext)
    for ax, (tag, label, R, m) in zip(np.atleast_1d(axs), runs):
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_facecolor('#9e9e9e')   # same extent in every panel
        pts = np.c_[R['x'], R['y']]; seg = np.stack([pts[:-1], pts[1:]], 1)
        h = np.nan_to_num(R['hdev'][:-1], nan=0).clip(0, 60)
        lc = LineCollection(seg, cmap=DEV, linewidth=np.where(R['tun'][:-1], 3.2, 1.4), zorder=3)
        lc.set_array(h); lc.set_clim(0, 60); ax.add_collection(lc)
        ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f'{label}\nheading deviation in tunnels: median {m["hdev_tunnel_p50"]:.0f}°, p90 {m["hdev_tunnel_p90"]:.0f}°\n'
                     f'{m["turn_reversals_per_m_tunnel"]:.2f} turn reversals per m', loc='left', fontsize=9.5)
    cb = fig.colorbar(lc, ax=axs, fraction=0.015, pad=0.03); cb.set_label('heading deviation from path (°)')
    fig.suptitle('Heading deviation along the driven path (thick = inside a tunnel)', x=0.01, ha='left', fontsize=11.5, color=T1)
    fig.savefig(out, facecolor=SURF, bbox_inches='tight'); plt.close(fig)


def metrics_figure(M, out):
    keys = [('hdev_tunnel_p50', 'Heading deviation in tunnels, median (°)'), ('hdev_tunnel_p90', 'Heading deviation in tunnels, p90 (°)'),
            ('turn_reversals_per_m_tunnel', 'Turn reversals per m in tunnels'), ('yaw_deg_per_m_tunnel', 'Yaw turned per m in tunnels (°/m)'),
            ('area_10min', 'Explored area at 10 min (m²)'), ('backup', 'BackUp recoveries')]
    fig, axs = plt.subplots(2, 3, figsize=(11, 6.4), dpi=150); fig.patch.set_facecolor(SURF)
    for ax, (k, title) in zip(axs.flat, keys):
        ax.set_facecolor(SURF); [ax.spines[s].set_visible(False) for s in ('top', 'right')]; ax.grid(axis='y', color=GRID, lw=0.8); ax.set_axisbelow(True)
        for x, (a, name, c) in enumerate(ARMS):
            v = [r[k] for r in M if r['run'].rsplit('_', 1)[0] == a and r[k] == r[k]]
            if not v: continue
            mean = float(np.mean(v)); ax.bar(x, mean, 0.6, color=c, zorder=2, alpha=0.9)
            ax.scatter(x + 0.17 + np.linspace(0, 0.1, len(v)), v, s=26, color='white', edgecolor=T1, linewidth=0.9, zorder=4)
            ax.annotate(f'{mean:.2f}' if mean < 1 else f'{mean:.1f}', (x - 0.08, mean), xytext=(0, 4), textcoords='offset points', ha='center', fontsize=8.5, color=T1)
        ax.set_xticks(range(len(ARMS))); ax.set_xticklabels(['NavFn', '+ smoothing', '+ smoothing\n+ MPPI tuning'], fontsize=8.5)
        ax.set_title(title, loc='left', fontsize=9.5); ax.set_ylim(0, None)
    fig.suptitle('Tunnel tracking: bars = mean, dots = runs (GUI runs, 10 min each)', x=0.01, ha='left', fontsize=11.5, color=T1)
    fig.tight_layout(); fig.savefig(out, facecolor=SURF); plt.close(fig)


def area_figure(RR, out):
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    [ax.spines[s].set_visible(False) for s in ('top', 'right')]; ax.grid(axis='y', color=GRID, lw=0.8)
    g = np.arange(0, DUR + 1, 5)
    for a, name, c in ARMS:
        curves = []
        for tag, R in RR.items():
            if tag.rsplit('_', 1)[0] != a: continue
            ar = [(t, v) for t, v in R['d']['area'] if t is not None]
            tt = np.array([q[0] for q in ar]); vv = np.array([q[1] for q in ar])
            yv = np.array([vv[tt <= q][-1] if (tt <= q).any() else 0 for q in g]); curves.append(yv)
            ax.step(g / 60, yv, where='post', color=c, lw=1, alpha=0.35)
        if curves:
            mm = np.mean(curves, 0); ax.step(g / 60, mm, where='post', color=c, lw=2.2, label=f'{name}  {mm[-1]:.1f} m²')
    ax.set_xlabel('time since first plan (min)'); ax.set_ylabel('explored free area (m²)'); ax.set_ylim(0, None); ax.legend(loc='upper left')
    ax.set_title('Explored area: runs (thin) and mean (bold)', loc='left', fontsize=11)
    fig.tight_layout(); fig.savefig(out, facecolor=SURF); plt.close(fig)


tags = sorted(os.path.basename(f)[:-5] for f in glob.glob(f'{D}/*_[0-9].json'))
M = []; RR = {}
for tag in tags:
    m, R = run_metrics(tag); M.append(m); RR[tag] = R
    trajectory_figure(tag, R, m, f'{F}/tunnel_traj_{tag}.png')
json.dump(M, open(f'{D}/tunnel_summary.json', 'w'), indent=1)
keys = [k for k in M[0] if k != 'run']
print(f"{'metric':30s}" + ''.join(f'{r["run"]:>10s}' for r in M))
for k in keys: print(f'{k:30s}' + ''.join(f'{r[k]:10.2f}' for r in M))
print(); print(f"{'metric (mean)':30s}" + ''.join(f'{a:>10s}' for a, _, _ in ARMS))
for k in keys:
    row = []
    for a, _, _ in ARMS:
        v = [r[k] for r in M if r['run'].rsplit('_', 1)[0] == a and r[k] == r[k]]
        row.append(f'{np.mean(v):10.2f}' if v else f'{"-":>10s}')
    print(f'{k:30s}' + ''.join(row))
if len(M) > 1:
    metrics_figure(M, f'{F}/tunnel_metrics.png'); area_figure(RR, f'{F}/tunnel_area.png')
    for n in sorted({t.rsplit('_', 1)[1] for t in tags}):
        runs = [(f'{a}_{n}', name, RR[f'{a}_{n}'], next(r for r in M if r['run'] == f'{a}_{n}')) for a, name, _ in ARMS if f'{a}_{n}' in RR]
        if len(runs) > 1: deviation_figure(runs, f'{F}/tunnel_deviation_run{n}.png')
