#!/usr/bin/env python3
"""Charts for docs/Comparisons.md. Every number below is copied from the note named in the
comment above it, so a chart can always be traced to its source.
Usage: python3 make_figures.py   (writes the PNGs next to this script)"""
import os, json
import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
C = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100']          # categorical slots 1-4 (validated)
SURF, T1, T2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': T2, 'axes.labelcolor': T2, 'xtick.color': T2,
                     'ytick.color': T2, 'axes.titlecolor': T1, 'legend.frameon': False})


def new(w=7.5, h=4.0, n=1, m=1):
    fig, axs = plt.subplots(n, m, figsize=(w, h), dpi=150); fig.patch.set_facecolor(SURF)
    for ax in np.atleast_1d(axs).flat:
        ax.set_facecolor(SURF); [ax.spines[s].set_visible(False) for s in ('top', 'right')]
        ax.grid(axis='y', color=GRID, lw=0.8); ax.set_axisbelow(True)
    return fig, axs


def save(fig, name, title):
    fig.suptitle(title, x=0.01, ha='left', fontsize=11.5, color=T1)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, name), facecolor=SURF); plt.close(fig)


def bar_labels(ax, bars, fmt='{:.0f}'):
    for b in bars:
        ax.annotate(fmt.format(b.get_height()), (b.get_x() + b.get_width() / 2, b.get_height()),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=8.5, color=T1)


def grouped(ax, groups, series, values, colors, fmt='{:.0f}'):
    n = len(series); w = 0.8 / n; x = np.arange(len(groups))
    for i, (s, c) in enumerate(zip(series, colors)):
        b = ax.bar(x + (i - (n - 1) / 2) * w, values[i], w * 0.92, color=c, label=s, zorder=3)
        bar_labels(ax, b, fmt)
    ax.set_xticks(x); ax.set_xticklabels(groups)


# 1. Frontier selection (concepts/Frontier exploration.md, 2026-09-27; one 30 min run each)
fig, ax = new(7.5, 4.2)
runs = [('global (original TAD)', [0, 5, 10, 15, 30], [0, 24.1, 60.8, 67.6, 77.4], C[0]),
        ('dfs, no shadow filter', [0, 5, 10, 15, 30], [0, 24.0, 31.0, 32.5, 73.4], C[1]),
        ('dfs (chosen)', [0, 5, 10, 15, 23], [0, 62.0, 72.8, 77.1, 78.0], C[2])]
for name, t, a, c in runs:
    ax.plot(t, a, color=c, lw=2, marker='o', ms=6, mec=SURF, mew=1.5, zorder=3)
    off = (-4, -11) if name.startswith('dfs (') else (6, 0)          # keep the end labels apart
    ax.annotate(f'{name}  {a[-1]:.1f} m²', (t[-1], a[-1]), xytext=off, textcoords='offset points',
                va='center', ha='right' if off[0] < 0 else 'left', fontsize=8.5, color=T1)
ax.axhline(83.1, color=T2, lw=1, ls='--'); ax.annotate('open floor 83.1 m²', (0.3, 83.1), xytext=(0, 4), textcoords='offset points', fontsize=8, color=T2)
ax.annotate('finished\n(/exploration_complete)', (23, 78.0), xytext=(45, -110), textcoords='offset points', fontsize=8, color=T2,
            arrowprops=dict(arrowstyle='-', color=T2, lw=0.8))
ax.set_xlim(0, 44); ax.set_ylim(0, 92); ax.set_xlabel('time (min)'); ax.set_ylabel('explored area (m²)')
save(fig, 'cmp_frontier_selection.png', 'Frontier selection: depth-first with the shadow filter finishes the cave')

# 2. Skid-steer calibration (robot/Gazebo simulation.md, 2026-09-26)
fig, ax = new(7.5, 3.8)
labels = ['geometric\n0.176 m', 'effective\n0.50 m', '0.43 m\n@0.3 rad/s', '0.43 m\n@0.6 rad/s', '0.43 m\n@1.0 rad/s']
vals = [0.35, 1.00, 1.08, 0.96, 0.90]
b = ax.bar(range(5), vals, 0.6, color=[C[1], C[0], C[2], C[2], C[2]], zorder=3); bar_labels(ax, b, '{:.2f}')
ax.axhline(1.0, color=T2, lw=1, ls='--'); ax.set_xticks(range(5)); ax.set_xticklabels(labels, fontsize=8.5)
ax.set_ylabel('achieved / commanded yaw rate'); ax.set_ylim(0, 1.3)
save(fig, 'cmp_track_width.png', 'Skid-steer track width: the robot only turns as commanded with the effective width')

# 3. Odometry fusion (robot/Odometry fusion.md, 2026-09-26)
fig, ax = new(6.5, 3.6)
b = ax.bar(['true yaw', 'EKF (wheels + gyro)', 'wheel odometry alone'], [82, 83, 184], 0.55, color=[T2, C[0], C[1]], zorder=3)
bar_labels(ax, b, '{:.0f}°'); ax.set_ylabel('yaw after the turn (°)'); ax.set_ylim(0, 210)
save(fig, 'cmp_odometry_fusion.png', 'Yaw after a 3.2 rad commanded turn: the gyro catches the wheel slip')

# 4. Rock climbing (robot/Rock climbing.md, 2026-09-26)
fig, ax = new(6.5, 3.8)
grouped(ax, ['rock under both tracks', 'rock under one side'], ['bogie first (current)', 'rocker first'],
        [[5, 6], [5, 8]], [C[0], C[1]], '{:.0f} cm')
ax.set_ylabel('largest rock crossed (cm)'); ax.set_ylim(0, 10); ax.legend(loc='upper left')
save(fig, 'cmp_rock_climbing.png', 'Rock climbing: rocker-first crosses taller one-sided rocks')

# 5. Inflation, BT and progress timeout (log/2026-10-05.md; one 5 min run each)
fig, ax = new(7.5, 3.9)
grouped(ax, ['inflation 0.30,\nold BT', 'inflation 0.22,\nold BT', 'inflation 0.22, new BT\n(BackUp first), 15 s progress'],
        ['goals reached', 'goals timed out'], [[2, 2, 4], [4, 3, 2]], [C[0], C[1]])
ax.set_ylabel('goals in 5 min'); ax.set_ylim(0, 5.2); ax.legend(loc='upper left')
save(fig, 'cmp_inflation_bt.png', 'Inflation and recovery order: thinner inflation + BackUp first reaches twice the goals')

# 6. EKF rate, startup turn (issues/Baseline runs 2026-10-08.md, follow-up 2026-10-09 and 2026-10-15)
fig, axs = new(9, 3.8, 1, 2)
data = {'10 Hz': ([180, 180, 62], [1406, 1429, 344]), '30 Hz': ([10, 76, 78, 12, 87, 65], [167, 358, 407])}
# 30 Hz overshoot: 3 runs on 2026-10-09 + 3 on 2026-10-15. Turning: only the 2026-10-09 runs are
# given per run (the 2026-10-15 runs report only their mean, 319°), so only those are plotted.
for ax, k, ttl, lim in ((axs[0], 0, 'overshoot after aligning (°)', 200), (axs[1], 1, 'total turning to the first goal (°)', 1600)):
    for x, (rate, c) in enumerate((('10 Hz', C[1]), ('30 Hz', C[0]))):
        v = data[rate][k]; jit = np.linspace(-0.08, 0.08, len(v))   # small spread so equal values stay visible
        ax.scatter(x + jit, v, s=44, color=c, edgecolor=SURF, linewidth=2, zorder=3)
        m = np.mean(v); ax.hlines(m, x - 0.22, x + 0.22, color=T1, lw=2, zorder=4)
        ax.annotate(f'{m:.0f}', (x + 0.26, m), va='center', fontsize=8.5, color=T1)
    ax.set_xticks([0, 1]); ax.set_xticklabels(['EKF 10 Hz', 'EKF 30 Hz']); ax.set_xlim(-0.5, 1.6); ax.set_ylim(0, lim)
    ax.set_title(ttl, loc='left', fontsize=9.5)
save(fig, 'cmp_ekf_rate.png', 'EKF rate and the startup turn: 30 Hz removes the multi-turn spins')

# 7. Startup hang (issues/Nav2 not loaded.md, 2026-10-15)
fig, ax = new(7.5, 3.4)
names = ['old (autostart)', 'ros2 service call after 8 s', 'lifecycle_startup node (chosen)']
ok = [7 / 8, 7 / 8, 12 / 12]; n = [8, 8, 12]
b = ax.barh(range(3), [100 * o for o in ok], 0.55, color=[C[1], C[1], C[0]], zorder=3)
for i, (o, k) in enumerate(zip(ok, n)):
    ax.annotate(f'{round(o * k)}/{k} came up', (100 * o, i), xytext=(4, 0), textcoords='offset points', va='center', fontsize=8.5, color=T1)
ax.set_yticks(range(3)); ax.set_yticklabels(names); ax.set_xlim(0, 125); ax.set_xlabel('launches where SLAM and Nav2 became active (%)')
ax.grid(axis='x', color=GRID, lw=0.8); ax.grid(axis='y', visible=False)
save(fig, 'cmp_startup_hang.png', 'Startup hang: starting Nav2 and SLAM from a node that waits 8 s fixed it')

# 8. TF rates (concepts/Relay rates.md, measured 2026-10-15)
fig, ax = new(7.5, 3.8)
grouped(ax, ['SLAM map→odom', 'EKF odom→base', 'robot_state_publisher'], ['on the robot (/tf)', 'on the mesh (/mesh/tf)'],
        [[51.7, 30.0, 20.0], [16.7, 10.0, 6.7]], [C[0], C[1]], '{:.1f}')
ax.set_ylabel('messages per second'); ax.set_ylim(0, 60); ax.legend(loc='upper right')
save(fig, 'cmp_tf_rates.png', 'TF: full rate for the robot, one third on the mesh (100 /s vs 33 /s)')

# 9. Planner, pooled (issues/Planner follow-ups 2026-10-18.md; n = 6 per planner)
fig, axs = new(10, 3.6, 1, 4)
pooled = [('Path turning (°/m)', 89.7, 47.3), ('Path kinks > 30° per m', 0.67, 0.02),
          ('Explored at 10 min (m²)', 63.6, 53.2), ('BackUp + Spin recoveries', 4.8, 11.3)]
for ax, (t, a, s) in zip(axs, pooled):
    b = ax.bar([0, 1], [a, s], 0.6, color=[C[0], C[1]], zorder=3); bar_labels(ax, b, '{:.2f}' if max(a, s) < 1 else '{:.1f}')
    ax.set_xticks([0, 1]); ax.set_xticklabels(['NavFn', 'Smac']); ax.set_title(t, loc='left', fontsize=9.5); ax.set_ylim(0, max(a, s) * 1.25)
save(fig, 'cmp_planner_pooled.png', 'NavFn vs Smac Lattice, 6 runs each: better paths, but no better exploration')

print('figures written to', OUT)
