#!/usr/bin/env python3
"""Explainer figure: what the sim 'track width' (0.34 vs 0.43) does, with real data from the
2026-10-20 GUI runs. Usage: track_width_explained.py RUN_DIR OUT.png
RUN_DIR holds refR_1.json (track 0.34) and track_3.json (track 0.43), from demo_recorder.py."""
import json, math, sys
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, Rectangle, FancyBboxPatch

D, OUT = sys.argv[1:3]
C34, C43 = '#2a78d6', '#eb6834'
SURF, T1, T2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': T2, 'xtick.color': T2, 'ytick.color': T2, 'axes.titlecolor': T1, 'axes.labelcolor': T2})
fig = plt.figure(figsize=(16, 13.5), dpi=150); fig.patch.set_facecolor(SURF)
gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 0.85], hspace=0.38, wspace=0.18, left=0.05, right=0.97, top=0.93, bottom=0.04)
fig.suptitle('Why the track-width number 0.34 vs 0.43 changes how the rover turns', x=0.05, ha='left', fontsize=17, color=T1, weight='bold')

def robot(ax, cx, cy, track_draw, label, col, arrows=None, ghost=None):
    """Top view of the rover: body, 3 wheels per side at the REAL spacing (176 mm),
    optional dashed 'pretend' wheels at the track-width value, and wheel-speed arrows."""
    ax.add_patch(FancyBboxPatch((cx - 99, cy - 71), 198, 142, boxstyle='round,pad=0,rounding_size=6', fc='#d8d8d8', ec=T1, lw=1.2))
    for sx in (-120, 0, 120):
        for sy in (-88, 88):
            ax.add_patch(Rectangle((cx + sx - 32, cy + sy - 12.5), 65, 25, fc='#404040', ec=T1, lw=0.8))
    if ghost:
        for sy in (-ghost / 2, ghost / 2):
            ax.add_patch(Rectangle((cx - 152, cy + sy - 12.5), 304, 25, fill=False, ec=col, lw=1.6, ls=(0, (4, 3))))
        ax.annotate('', (cx + 175, cy - ghost / 2), (cx + 175, cy + ghost / 2), arrowprops=dict(arrowstyle='<|-|>', color=col, lw=1.3))
        ax.text(cx + 183, cy, f'pretend\n{label}', color=col, fontsize=10, va='center', weight='bold')
    if arrows:
        for sy, L in ((88, arrows), (-88, -arrows)):
            ax.add_patch(FancyArrow(cx - 60, cy + sy, L, 0, width=9, head_width=26, head_length=22, length_includes_head=True, color=col, ec=T1, lw=0.5, zorder=5))
    ax.add_patch(FancyArrow(cx, cy, 70, 0, width=4, head_width=16, head_length=16, color=T2, zorder=6))

# ---------------- panel 1: how a skid-steer turns, and why the number is "pretend" ----------------
ax = fig.add_subplot(gs[0, 0]); ax.set_aspect('equal'); ax.axis('off')
ax.set_title('1. The robot turns like a tank: left and right wheels at different speeds', loc='left', fontsize=12)
robot(ax, 0, 0, 176, '', T2)
ax.annotate('', (-200, -88), (-200, 88), arrowprops=dict(arrowstyle='<|-|>', color=T1, lw=1.3)); ax.text(-208, 0, 'real wheel\nspacing\n176 mm', ha='right', va='center', fontsize=10)
ax.text(0, -175, 'Turning on the spot, the front and back wheels must SLIDE sideways (rubber scrubbing on the floor),\n'
        'so the robot turns much less than the wheel speeds suggest. With the real 176 mm in the formula it\n'
        'reached only ~35 % of the commanded turn. So the software PRETENDS the wheels are further apart:\n'
        'that makes the wheels spin faster per command and makes up for the sliding.\n\n'
        '      wheel speed  =  turn command  ×  track width  ÷ 2          (track width = the pretend number)',
        ha='center', va='top', fontsize=10, color=T1)
ax.set_xlim(-330, 330); ax.set_ylim(-330, 130)

# ---------------- panel 2: same command, two numbers ----------------
ax = fig.add_subplot(gs[0, 1]); ax.set_aspect('equal'); ax.axis('off')
ax.set_title('2. Same command "turn at 0.5 rad/s": how hard the wheels are driven', loc='left', fontsize=12)
v43, v34 = 0.5 * 0.43 / 2, 0.5 * 0.34 / 2
robot(ax, -330, 0, 176, '0.43 m', C43, arrows=v43 * 1300, ghost=430 * 0.55)
robot(ax, 330, 0, 176, '0.34 m', C34, arrows=v34 * 1300, ghost=340 * 0.55)
ax.text(-330, -175, f'track 0.43 → each side {v43 * 1000:.0f} mm/s\nwheels push HARDER into the turn', ha='center', va='top', fontsize=11, color=C43, weight='bold')
ax.text(330, -175, f'track 0.34 → each side {v34 * 1000:.0f} mm/s\nwheels push ~21 % SOFTER', ha='center', va='top', fontsize=11, color=C34, weight='bold')
ax.text(0, -255, 'Once a turn is under way, the sliding limits the speed, so both settle at about the same turn rate (step test).\n'
        'The difference is in how hard the robot is shoved into each turn and each correction.', ha='center', va='top', fontsize=10, color=T2)
ax.set_xlim(-620, 640); ax.set_ylim(-330, 160)

# ---------------- data ----------------
def load(tag):
    d = json.load(open(f'{D}/{tag}.json')); S = [s for s in d['samples'] if s['t'] <= 45]
    C = np.array([c for c in d['cmd'] if c[0] <= 45])
    return d, S, C
runs = [('track_3', 'track 0.43 (run track_3)', C43), ('refR_1', 'track 0.34 (run refR_1)', C34)]

# ---------------- panel 3: heading error over time ----------------
ax = fig.add_subplot(gs[1, 0]); ax.set_facecolor(SURF); [ax.spines[s].set_visible(False) for s in ('top', 'right')]
ax.grid(axis='y', color=GRID, lw=0.8)
for tag, lab, col in runs:
    d, S, C = load(tag)
    t = np.array([s['t'] for s in S]); h = np.array([abs(s.get('hdev', np.nan)) for s in S])
    ax.plot(t, h, color=col, lw=2.2, label=lab)
ax.axhspan(0, 15, color='#e8f3e8', zorder=0); ax.text(44, 7, 'facing the path', ha='right', va='center', fontsize=9, color='#2f7a2f')
ax.set_ylim(0, 190); ax.set_xlim(0, 45); ax.set_xlabel('seconds after the first goal (goal starts straight behind: 180°)'); ax.set_ylabel('how far it points away from the path (°)')
ax.set_title('3. Real start-up turn: heading error over time', loc='left', fontsize=12)
ax.legend(loc='upper right', frameon=False)
ax.annotate('0.43: reaches the path direction at 14 s,\nswings straight past it and round again,\nonly settles at 40 s (200° of turning)', (20.5, 172), (24.5, 160), fontsize=9.5, color=C43, va='top', arrowprops=dict(arrowstyle='-', color=C43, lw=0.8))
ax.annotate('0.34: no overshoot, but turns slowly while\nreversing in an arc; still ~50° off after 45 s\n(gentle = predictable, but hesitant)', (31, 85), (14.5, 36), fontsize=9.5, color=C34, arrowprops=dict(arrowstyle='-', color=C34, lw=0.8))

# ---------------- panel 4: what it looks like from above ----------------
ax = fig.add_subplot(gs[1, 1]); ax.set_aspect('equal'); ax.set_facecolor(SURF); [ax.spines[s].set_visible(False) for s in ('top', 'right')]
for k, (tag, lab, col) in enumerate(runs):
    d, S, C = load(tag); off = (0.0, 0.55 * (1 - 2 * k))
    x = np.array([s['x'] for s in S]) + off[0]; y = np.array([s['y'] for s in S]) + off[1]; yaw = np.array([s['yaw'] for s in S])
    ax.plot(x, y, color=col, lw=2, alpha=0.9)
    for i in range(0, len(S), 15):       # heading arrow every 1.5 s
        ax.add_patch(FancyArrow(x[i], y[i], 0.12 * math.cos(yaw[i]), 0.12 * math.sin(yaw[i]), width=0.008, head_width=0.035, head_length=0.03, color=col, alpha=0.85))
    ax.text(x[0] + 0.12, y[0] + 0.08, f'{lab}\nstart', fontsize=9, color=col)
ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)  (the two runs drawn 1.1 m apart)')
ax.set_title('4. Same 45 s from above (arrow = where it points, every 1.5 s)', loc='left', fontsize=12)
ax.text(0.0, -0.2, 'Orange: arrows fan round in place (spinning).\nBlue: arrows still point forward while it backs away (reversing, turning slowly).',
        transform=ax.transAxes, fontsize=9, color=T2, va='top')

# ---------------- panel 5: the trade-off ----------------
ax = fig.add_subplot(gs[2, :]); ax.axis('off')
ax.set_title('5. The trade-off (3 GUI runs each, cave explored to 90 % or 40 min)', loc='left', fontsize=12)
rows = [('', 'track 0.43', 'track 0.34', 'better'),
        ('Spins (≥ 300° in 60 s, per run)', '3–4', '0', '0.34'),
        ('Turning at start-up (goal behind)', '142–185°', '43°', '0.34'),
        ('Large deviations from the path in open areas', '≈ 8 %', '1–3 %', '0.34'),
        ('Time stuck (mostly turning round in tight dead ends)', '17–21 %', '31–33 %', '0.43'),
        ('Steady turn speed once turning (step test, no Nav2)', 'about the same', 'about the same', '–')]
for i, r in enumerate(rows):
    y = 0.86 - i * 0.135
    for x, txt, w in zip((0.0, 0.47, 0.64, 0.82), r, (0.45, 0.16, 0.16, 0.12)):
        col = C43 if (x == 0.47 and i) else C34 if (x == 0.64 and i) else T1
        if x == 0.82 and i: col = C34 if txt == '0.34' else C43 if txt == '0.43' else T2
        ax.text(x, y, txt, fontsize=11.5, color=col, weight='bold' if i == 0 or x == 0.82 else 'normal', transform=ax.transAxes, va='center')
    ax.plot([0, 0.95], [y - 0.065] * 2, color=GRID, lw=0.8, transform=ax.transAxes)
ax.text(0.0, -0.06, 'In one sentence: 0.34 pushes the wheels more gently into every turn, so the robot never overshoots (no spins, stays on the path),\n'
        'but it is slow to turn round, and in a tight dead end the gentle push is sometimes not enough to turn against the walls.',
        fontsize=11, color=T1, transform=ax.transAxes, va='top')
fig.savefig(OUT, facecolor=SURF); print('written', OUT)
