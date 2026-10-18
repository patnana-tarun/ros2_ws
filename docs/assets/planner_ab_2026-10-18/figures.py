#!/usr/bin/env python3
"""Figures for the planner A/B. Usage: figures.py <bench dir with *_N.json + summary.json> <output dir>"""
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
B, A = sys.argv[1:3]
C = {'navfn': '#2a78d6', 'smac': '#eb6834'}; NAME = {'navfn': 'NavFn (current)', 'smac': 'Smac Lattice'}
SURF, T1, T2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': T2, 'axes.labelcolor': T2, 'xtick.color': T2, 'ytick.color': T2, 'axes.titlecolor': T1})


def style(ax):
    ax.set_facecolor(SURF); [ax.spines[s].set_visible(False) for s in ('top', 'right')]
    ax.grid(axis='y', color=GRID, lw=0.8); ax.set_axisbelow(True)


fig, ax = plt.subplots(figsize=(8, 4.4), dpi=150); fig.patch.set_facecolor(SURF); style(ax)
g = np.arange(0, 601, 5)
for k in ('navfn', 'smac'):
    curves = []
    for i in (1, 2, 3):
        d = json.load(open(f'{B}/{k}_{i}.json')); ar = [(t, a) for t, a, _ in d['area'] if t is not None]
        t = np.array([x[0] for x in ar]); a = np.array([x[1] for x in ar])
        y = np.array([a[t <= x][-1] if (t <= x).any() else 0 for x in g]); curves.append(y)
        ax.step(g / 60, y, where='post', color=C[k], lw=1, alpha=0.35)
    m = np.mean(curves, axis=0); ax.step(g / 60, m, where='post', color=C[k], lw=2.2)
    ax.annotate(f'{NAME[k]}  {m[-1]:.1f} m²', (10, m[-1]), xytext=(6, 6 if k == 'navfn' else -12), textcoords='offset points', color=T1, fontsize=9, va='center')
ax.set_xlim(0, 12.2); ax.set_ylim(0, None); ax.set_xlabel('time since first plan (min)'); ax.set_ylabel('explored free area (m²)')
ax.set_title('Explored area, 3 runs per planner (thin) and mean (bold)', loc='left', fontsize=11)
fig.tight_layout(); fig.savefig(f'{A}/planner_ab_area.png', facecolor=SURF); plt.close(fig)

R = {r['run']: r for r in json.load(open(f'{B}/summary.json'))['rows']}
M = [('path_turn_deg_per_m', 'Path turning (°/m)'), ('path_kinks30_per_m', 'Kinks > 30° per m'), ('plans_per_min', 'Replans per min'),
     ('progress_fail', '"Failed to make progress"'), ('stall_time_s', 'Stall time (s)'), ('plan_fail', 'Planning failures'),
     ('area_10min', 'Explored area at 10 min (m²)'), ('xte_gt10cm_pct', 'Time > 10 cm off path (%)'), ('planner_cpu_s', 'planner_server CPU (s)')]
fig, axs = plt.subplots(3, 3, figsize=(9, 7.2), dpi=150); fig.patch.set_facecolor(SURF)
for ax, (k, title) in zip(axs.flat, M):
    style(ax)
    for x, p in enumerate(('navfn', 'smac')):
        v = [R[f'{p}_{i}'][k] for i in (1, 2, 3)]; m = np.mean(v)
        ax.scatter([x] * 3, v, s=46, color=C[p], edgecolor=SURF, linewidth=2, zorder=3)
        ax.hlines(m, x - 0.22, x + 0.22, color=T1, lw=2, zorder=4)
        ax.annotate(f'{m:.2f}' if abs(m) < 1 else f'{m:.1f}', (x + 0.25, m), va='center', fontsize=8.5, color=T1)
    ax.set_xticks([0, 1]); ax.set_xticklabels(['NavFn', 'Smac']); ax.set_xlim(-0.5, 1.7); ax.set_ylim(0, None)
    ax.set_title(title, loc='left', fontsize=9.5)
fig.suptitle('Per-run values (dots) and mean (bar), 10 min headless runs', x=0.01, ha='left', fontsize=11, color=T1)
fig.tight_layout(); fig.savefig(f'{A}/planner_ab_metrics.png', facecolor=SURF); plt.close(fig)
print('ok')
