#!/usr/bin/env python3
"""Slide 23 run maps: the same whole-run card for the run before the speed fixes and one after them.

  before: ~/tunnelrev_runs_2026-10-20/combined/trg_1  (tunnel-reverse + radius + guarded retrace, the run
          on slide 23 so far; recorder json + launch log + map npz)
  after:  tools/rover_mcp/runs/20261026_113847_slide_gifs_mapfill  (current nav-speed config, rover track.npz)

Style follows docs/assets/navigation/tunnel-reverse/analyze_tr.py run_card (route over the final SLAM map,
coloured by sim minutes, goals marked), with fewer, larger numbers for a slide. Both maps share one
colour scale so the minutes compare directly.
Definitions as in analyze_tr.py: stuck sample = net displacement over t-30 .. t+30 s < 0.5 m.
Usage: run_maps.py [before_dir/tag] [after_run_dir]
"""
import json, os, re, sys
import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

HERE = os.path.dirname(os.path.abspath(__file__))
BEFORE = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/tunnelrev_runs_2026-10-20/combined/trg_1')
AFTER = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '../../../../tools/rover_mcp/runs/20261026_113847_slide_gifs_mapfill')
STUCK_WIN, STUCK_R = 30.0, 0.5
TMAX = 17.0                                    # shared colour scale, sim minutes
SURF, T1, T2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
OK, BAD = '#0ca30c', '#d03b3b'
plt.rcParams.update({'font.size': 12, 'axes.edgecolor': T2, 'axes.labelcolor': T2, 'xtick.color': T2,
                     'ytick.color': T2, 'axes.titlecolor': T1, 'legend.frameon': False})


def stuck_mask(t, x, y):
    lo = np.searchsorted(t, t - STUCK_WIN); hi = np.clip(np.searchsorted(t, t + STUCK_WIN), 0, len(t) - 1)
    return np.hypot(x[hi] - x[lo], y[hi] - y[lo]) < STUCK_R


def load_before(base):
    d = json.load(open(base + '.json')); S = d['samples']
    t = np.array([s['t'] for s in S]); w = np.array([s['w'] for s in S])
    x = np.array([s['x'] for s in S]); y = np.array([s['y'] for s in S]); vx = np.array([s['vx'] for s in S])
    z = np.load(base + '_map.npz')
    goals, sent = [], None                     # (kind, sim t, (x, y)) from the launch log (wall clock)
    for l in open(base + '.launch.log', errors='ignore'):
        l = re.sub(r'\x1b\[[0-9;]*m', '', l); m = re.search(r'\[(\d{10}\.\d+)\]', l)
        if not m: continue
        tw = float(m.group(1)) - d['wall_start']
        if tw < 0 or tw > d['wall_s']: continue
        ts = float(np.interp(tw, w, t))
        if (g := re.search(r'Sending goal: \(([-0-9.]+), ([-0-9.]+)\)', l)): sent = (float(g[1]), float(g[2]))
        elif 'Reached goal' in l and sent: goals.append(('reached', ts, sent)); sent = None
        elif 'gave up on the goal' in l and sent: goals.append(('failed', ts, sent)); sent = None
    cov = np.array([[q[0], q[2]] for q in d['cov']])
    return dict(t=t, x=x, y=y, vx=vx, grid=z['data'], res=float(z['res']), ox=float(z['ox']), oy=float(z['oy']),
                goals=goals, cov=cov, label='Before the speed fixes', sub='tunnel-reverse, 2026-10-20')


def load_after(run):
    z = np.load(os.path.join(run, 'track.npz'))
    goals, sent = [], None
    for e in z['goal_events']:
        ts, kind, msg = e.split('|', 2); ts = float(ts)
        if (g := re.search(r'Sending goal: \(([-0-9.]+), ([-0-9.]+)\)', msg)): sent = (float(g[1]), float(g[2]))
        elif kind == 'reached' and sent: goals.append(('reached', ts, sent)); sent = None
        elif kind == 'gave_up' and sent: goals.append(('failed', ts, sent)); sent = None
    return dict(t=z['t'], x=z['x'], y=z['y'], vx=z['vx'], grid=z['map'], res=float(z['map_res']),
                ox=float(z['map_origin'][0]), oy=float(z['map_origin'][1]), goals=goals,
                cov=np.c_[z['cov'][:, 0], z['cov'][:, 3]], label='After the speed fixes', sub='final navigation, 2026-10-26')


def metrics(R):
    t, x, y, cov = R['t'], R['x'], R['y'], R['cov']
    t90 = next((q[0] for q in cov if q[1] >= 90.0), np.nan)
    t95 = next((q[0] for q in cov if q[1] >= 95.0), np.nan)
    st = stuck_mask(t, x, y)
    rev = np.r_[np.hypot(np.diff(x), np.diff(y)), 0][R['vx'] < -0.02].sum()
    return dict(t90=t90 / 60, t95=t95 / 60, final=cov[-1, 1], dur=t[-1] / 60,
                dist=float(np.hypot(np.diff(x), np.diff(y)).sum()), rev=float(rev), stuck=100 * float(st.mean()),
                reached=sum(g[0] == 'reached' for g in R['goals']), failed=sum(g[0] == 'failed' for g in R['goals']),
                stuck_mask=st, i90=int(np.searchsorted(t, t90)) if t90 == t90 else None)


def draw(ax, R, M, legend=True):
    g = R['grid']; img = np.full(g.shape + (3,), 0.80); img[g == 0] = 1.0; img[g >= 65] = 0.10
    ax.imshow(img, origin='lower', interpolation='nearest',
              extent=[R['ox'], R['ox'] + g.shape[1] * R['res'], R['oy'], R['oy'] + g.shape[0] * R['res']])
    pts = np.c_[R['x'], R['y']]; seg = np.stack([pts[:-1], pts[1:]], 1)
    lc = LineCollection(seg, cmap='viridis', linewidth=3.0, zorder=3); lc.set_array(R['t'][:-1] / 60); lc.set_clim(0, TMAX)
    ax.add_collection(lc)
    st = M['stuck_mask']
    if st.any(): ax.scatter(R['x'][st][::10], R['y'][st][::10], s=10, c=BAD, alpha=0.35, zorder=4,
                            label='stuck (moved < 0.5 m in 60 s)' if legend else None)
    for kind, col, name in (('reached', OK, 'goal reached'), ('failed', BAD, 'goal given up')):
        p = [g[2] for g in R['goals'] if g[0] == kind]
        if p: ax.scatter(*np.array(p).T, s=70, c=col, edgecolor='black', linewidth=0.7, zorder=5, label=name if legend else None)
    ax.scatter(R['x'][0], R['y'][0], marker='s', s=80, c='white', edgecolor='black', zorder=6, label='start' if legend else None)
    if M['i90'] is not None:
        k = min(M['i90'], len(R['x']) - 1)
        ax.scatter(R['x'][k], R['y'][k], marker='*', s=320, c='#fab219', edgecolor='black', linewidth=0.8, zorder=7,
                   label='90 % explored here' if legend else None)
    ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    return lc


def numbers(tx, M, headline_color):
    f = lambda v, fmt: '—' if v != v else fmt.format(v)
    tx.axis('off')
    tx.text(0, 0.97, f(M['t90'], '{:.1f} min'), fontsize=34, weight='bold', color=headline_color, transform=tx.transAxes, va='top')
    tx.text(0, 0.80, 'to explore 90 % of the cave', fontsize=13, color=T2, transform=tx.transAxes, va='top')
    rows = [('Final coverage', f(M['final'], '{:.1f} %')), ('Time to 95 %', f(M['t95'], '{:.1f} min')),
            ('Distance driven', f(M['dist'], '{:.0f} m')), ('Time stuck', f(M['stuck'], '{:.0f} %')),
            ('Goals reached / given up', f'{M["reached"]} / {M["failed"]}')]
    yy = 0.66
    for k, v in rows:
        tx.text(0, yy, k, fontsize=13, color=T2, transform=tx.transAxes)
        tx.text(1, yy, v, fontsize=13, color=T1, ha='right', weight='bold', transform=tx.transAxes)
        tx.plot([0, 1], [yy - 0.03] * 2, color=GRID, lw=0.8, transform=tx.transAxes); yy -= 0.12


def card(R, M, out, color):
    fig = plt.figure(figsize=(13.33, 6.4), dpi=150); fig.patch.set_facecolor(SURF)
    ax = fig.add_axes([0.01, 0.04, 0.66, 0.84]); tx = fig.add_axes([0.72, 0.24, 0.26, 0.64])
    lc = draw(ax, R, M)
    fig.text(0.015, 0.94, R['label'], fontsize=20, weight='bold', color=T1)
    fig.text(0.015, 0.905, R['sub'], fontsize=12, color=T2)
    cb = fig.colorbar(lc, ax=ax, fraction=0.025, pad=0.005); cb.set_label('sim minutes'); cb.outline.set_visible(False)
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, loc='lower left', bbox_to_anchor=(0.715, 0.03), ncol=1, fontsize=10.5)
    numbers(tx, M, color)
    fig.savefig(out, facecolor=SURF); plt.close(fig); print('wrote', out)


def pair(Rb, Mb, Ra, Ma, out):
    fig = plt.figure(figsize=(13.33, 7.0), dpi=150); fig.patch.set_facecolor(SURF)
    for i, (R, M, col) in enumerate(((Rb, Mb, BAD), (Ra, Ma, OK))):
        x0 = 0.01 + 0.495 * i
        ax = fig.add_axes([x0, 0.20, 0.47, 0.66]); lc = draw(ax, R, M, legend=(i == 0))
        fig.text(x0 + 0.005, 0.93, R['label'], fontsize=18, weight='bold', color=T1)
        fig.text(x0 + 0.005, 0.895, f'90 % in {M["t90"]:.1f} min   ·   stuck {M["stuck"]:.0f} %   ·   '
                 f'goals given up {M["failed"]}', fontsize=13, color=col, weight='bold')
    h, l = fig.axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower left', bbox_to_anchor=(0.01, 0.02), ncol=3, fontsize=11)
    cax = fig.add_axes([0.66, 0.09, 0.31, 0.025]); cb = fig.colorbar(lc, cax=cax, orientation='horizontal')
    cb.set_label('sim minutes (same scale on both maps)'); cb.outline.set_visible(False)
    fig.savefig(out, facecolor=SURF); plt.close(fig); print('wrote', out)


Rb, Ra = load_before(BEFORE), load_after(AFTER)
Mb, Ma = metrics(Rb), metrics(Ra)
for n, M in (('before', Mb), ('after', Ma)):
    print(n, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in M.items() if k not in ('stuck_mask',)})
card(Rb, Mb, os.path.join(HERE, 'slide23_before.png'), BAD)
card(Ra, Ma, os.path.join(HERE, 'slide23_after.png'), OK)
pair(Rb, Mb, Ra, Ma, os.path.join(HERE, 'slide23_before_after.png'))
