#!/usr/bin/env python3
"""Per-arm figure for the 4-arm follow-up. Usage: figures_arms.py <bench dir with summary.json> <output png>"""
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
B, OUT = sys.argv[1:3]
ARMS = [('navfn', 'NavFn', '#2a78d6'), ('smac', 'Smac', '#eb6834'), ('smacpc', 'Smac\n+pre-check', '#1baf7a'), ('smacpcw', 'Smac\n+pre-check\n+wide infl.', '#eda100')]
SURF, T1, T2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': T2, 'axes.labelcolor': T2, 'xtick.color': T2, 'ytick.color': T2, 'axes.titlecolor': T1})
R = {r['run']: r for r in json.load(open(f'{B}/summary.json'))['rows']}
M = [('area_10min', 'Explored area at 10 min (m²)'), ('stall_time_s', 'Stall time (s)'), ('progress_fail', '"Failed to make progress"'),
     ('plan_fail_distinct_goals', 'Goals the planner refused'), ('path_kinks30_per_m', 'Path kinks > 30° per m'), ('path_turn_deg_per_m', 'Path turning (°/m)')]
fig, axs = plt.subplots(2, 3, figsize=(11, 6.6), dpi=150); fig.patch.set_facecolor(SURF)
for ax, (k, title) in zip(axs.flat, M):
    ax.set_facecolor(SURF); [ax.spines[s].set_visible(False) for s in ('top', 'right')]; ax.grid(axis='y', color=GRID, lw=0.8); ax.set_axisbelow(True)
    for x, (a, name, c) in enumerate(ARMS):
        v = [R[f'{a}_{i}'][k] for i in (1, 2, 3)]; m = np.mean(v)
        ax.scatter([x] * 3, v, s=40, color=c, edgecolor=SURF, linewidth=2, zorder=3)
        ax.hlines(m, x - 0.25, x + 0.25, color=T1, lw=2, zorder=4)
        ax.annotate(f'{m:.2f}' if abs(m) < 1 else (f'{m:.1f}' if abs(m) < 20 else f'{m:.0f}'), (x + 0.28, m), va='center', fontsize=8, color=T1)
    ax.set_xticks(range(len(ARMS))); ax.set_xticklabels([n for _, n, _ in ARMS], fontsize=7.5); ax.set_xlim(-0.5, len(ARMS) - 0.2); ax.set_ylim(0, None)
    ax.set_title(title, loc='left', fontsize=9.5)
fig.suptitle('Follow-up benchmark: 4 arms side by side, 3 rounds × 10 min (dots = runs, bar = mean)', x=0.01, ha='left', fontsize=11, color=T1)
fig.tight_layout(); fig.savefig(OUT, facecolor=SURF); print('ok')
