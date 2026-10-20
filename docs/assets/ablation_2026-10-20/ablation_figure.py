#!/usr/bin/env python3
"""Ablation chart (2026-10-20). Usage: ablation_figure.py validation.json out.png"""
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
R = json.load(open(sys.argv[1]))
ARMS = [('tuned', 'before\n(tuned)', '#1baf7a'), ('demo2', 'demo v2\n(all fixes)', '#2a78d6'), ('unk', 'A: unknown\npolicy undone', '#86b6ef'),
        ('hand', 'B: hand-over\nundone', '#86b6ef'), ('track', 'C: track 0.43\n(undone)', '#eb6834'), ('prechk', 'D: pre-check\nundone', '#86b6ef')]
K = [('stuck_pct', 'Time stuck (%)'), ('cmd_wz_absmax', 'Largest MPPI turn command (rad/s)'), ('startup_turn_deg', 'Start-up turning, goal behind (°)'),
     ('rotations_300', 'Spins: ≥ 300° in 60 s (per run)'), ('open_big_pct', 'Large open-area deviations (%)'), ('goal_success_pct', 'Goal success (%)')]
SURF, T1, T2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': T2, 'xtick.color': T2, 'ytick.color': T2, 'axes.titlecolor': T1})
fig, axs = plt.subplots(2, 3, figsize=(14, 7), dpi=150); fig.patch.set_facecolor(SURF)
for ax, (k, ttl) in zip(axs.flat, K):
    ax.set_facecolor(SURF); [ax.spines[s].set_visible(False) for s in ('top', 'right')]; ax.grid(axis='y', color=GRID, lw=0.8); ax.set_axisbelow(True)
    for x, (a, lab, c) in enumerate(ARMS):
        v = [r[k] for r in R if r['run'].rsplit('_', 1)[0] == a]; m = float(np.mean(v))
        ax.bar(x, m, 0.62, color=c, zorder=2)
        ax.scatter(x + 0.18 + np.linspace(0, 0.1, len(v)), v, s=20, color='white', edgecolor=T1, linewidth=0.8, zorder=4)
        ax.annotate(f'{m:.2f}' if m < 1 else f'{m:.0f}', (x - 0.08, m), xytext=(0, 3), textcoords='offset points', ha='center', fontsize=8, color=T1)
    ax.set_xticks(range(len(ARMS))); ax.set_xticklabels([l for _, l, _ in ARMS], fontsize=7.2); ax.set_title(ttl, loc='left', fontsize=10); ax.set_ylim(0, None)
fig.suptitle('Ablation: each variant undoes one demo fix (3 GUI runs each; bars = mean, dots = runs)', x=0.01, ha='left', fontsize=12, color=T1)
fig.tight_layout(); fig.savefig(sys.argv[2], facecolor=SURF)
