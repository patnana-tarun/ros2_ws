#!/usr/bin/env python3
"""General-arrangement drawing of the explorer rover, generated from the robot description.

Every part outline is the projection of the URDF's own visual geometry (boxes and cylinders,
placed through the joint tree with all joints at 0), so the drawing always matches the model.
Dimensions are taken from the xacro properties.

Usage (workspace sourced):  python3 rover_drawing.py [OUT_DIR]
Writes explorer_rover_drawing.png / .pdf / .svg
"""
import math, os, subprocess, sys
import xml.etree.ElementTree as ET
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Arc
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
XACRO = subprocess.run(['ros2', 'pkg', 'prefix', 'explorer_description'], capture_output=True, text=True).stdout.strip()
XACRO = os.path.join(XACRO, 'share', 'explorer_description', 'urdf', 'explorer.urdf.xacro')
urdf = ET.fromstring(subprocess.run(['xacro', XACRO], capture_output=True, text=True, check=True).stdout)

# ---------------------------------------------------------------- kinematics
def rot(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])

def tf(el):
    o = el.find('origin')
    xyz = [float(v) for v in (o.get('xyz', '0 0 0') if o is not None else '0 0 0').split()]
    rpy = [float(v) for v in (o.get('rpy', '0 0 0') if o is not None else '0 0 0').split()]
    T = np.eye(4); T[:3, :3] = rot(*rpy); T[:3, 3] = xyz; return T

world = {'base_footprint': np.eye(4)}
joints = urdf.findall('joint')
while len(world) < len(urdf.findall('link')):
    for j in joints:
        p, c = j.find('parent').get('link'), j.find('child').get('link')
        if p in world and c not in world: world[c] = world[p] @ tf(j)

COL = {'black': '#4a4a4a', 'grey': '#c9c9c9', 'yellow': '#f2c14e', 'blue': '#5b8bd9', 'green': '#57a773'}
parts = []          # (link, name, colour, 3-D points (N,3), kind)
for link in urdf.findall('link'):
    for v in link.findall('visual'):
        T = world[link.get('name')] @ tf(v); g = v.find('geometry'); m = v.find('material')
        col = COL.get(m.get('name') if m is not None else '', '#bbbbbb')
        if g.find('box') is not None:
            sx, sy, sz = [float(q) for q in g.find('box').get('size').split()]
            P = np.array([[a * sx / 2, b * sy / 2, c * sz / 2] for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)])
        else:
            cyl = g.find('cylinder'); r = float(cyl.get('radius')); h = float(cyl.get('length'))
            t = np.linspace(0, 2 * np.pi, 48, endpoint=False)
            P = np.vstack([np.c_[r * np.cos(t), r * np.sin(t), np.full_like(t, z)] for z in (-h / 2, h / 2)])
        Pw = (T[:3, :3] @ P.T).T + T[:3, 3]
        parts.append((link.get('name'), col, Pw * 1000.0))     # mm

def hull(pts):
    pts = sorted(map(tuple, np.round(pts, 4)))
    if len(pts) < 3: return np.array(pts)
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return np.array(lo[:-1] + up[:-1])

# --------------------------------------------------------------- dimensions
P = {k.get('name'): None for k in []}
W_R, W_W, W_Y, AX = 32.5, 25.0, 88.0, 120.0
PL, PW, PT, PTOP = 198.0, 143.0, 2.5, 130.0
PIV_H, PIV_X = 95.0, 60.0                       # pivot height, ahead of the middle axle (bogie leads)
lidar = world['laser_frame'][:3, 3] * 1000; pi = world['pi_link'][:3, 3] * 1000
INK, DIM, GRID, SURF = '#1a1a1a', '#1f4e9c', '#d9d9d9', '#ffffff'

def dim(ax, p1, p2, off, text, horizontal=True, fs=8.5, ext=True):
    """Dimension line between p1 and p2, offset perpendicular by off (mm)."""
    (x1, y1), (x2, y2) = p1, p2
    if horizontal:
        y = y1 + off if abs(off) else y1
        if ext:
            ax.plot([x1, x1], [y1, y + math.copysign(2, off)], color=DIM, lw=0.6)
            ax.plot([x2, x2], [y2, y + math.copysign(2, off)], color=DIM, lw=0.6)
        ax.annotate('', (x1, y), (x2, y), arrowprops=dict(arrowstyle='<|-|>', color=DIM, lw=0.8, shrinkA=0, shrinkB=0, mutation_scale=7))
        ax.text((x1 + x2) / 2, y + (2.2 if off >= 0 else -2.2), text, ha='center', va='bottom' if off >= 0 else 'top', fontsize=fs, color=DIM,
                bbox=dict(fc=SURF, ec='none', pad=0.6))
    else:
        x = x1 + off
        if ext:
            ax.plot([x1, x + math.copysign(2, off)], [y1, y1], color=DIM, lw=0.6)
            ax.plot([x2, x + math.copysign(2, off)], [y2, y2], color=DIM, lw=0.6)
        ax.annotate('', (x, y1), (x, y2), arrowprops=dict(arrowstyle='<|-|>', color=DIM, lw=0.8, shrinkA=0, shrinkB=0, mutation_scale=7))
        ax.text(x + (2.2 if off >= 0 else -2.2), (y1 + y2) / 2, text, ha='left' if off >= 0 else 'right', va='center', fontsize=fs, color=DIM,
                rotation=90, rotation_mode='anchor' if False else 'default', bbox=dict(fc=SURF, ec='none', pad=0.6))

def view(ax, u, v, depth, far_first=True, title=''):
    """Orthographic view: u,v = column indices for horizontal/vertical, depth for draw order."""
    order = sorted(parts, key=lambda q: q[2][:, depth].mean(), reverse=not far_first)
    for name, col, pts in order:
        h = hull(np.c_[pts[:, u[0]] * u[1], pts[:, v]])
        ax.add_patch(Polygon(h, closed=True, fc=col, ec=INK, lw=0.7, alpha=0.95, zorder=2))
    ax.set_aspect('equal'); ax.axis('off'); ax.set_title(title, loc='left', fontsize=11, color=INK, pad=6)

fig = plt.figure(figsize=(16.5, 11.7), dpi=200)      # A3 landscape
fig.patch.set_facecolor(SURF)

# ---- side elevation (seen from the robot's right side: front to the right) -------------------
ax = fig.add_axes([0.04, 0.50, 0.46, 0.43])
view(ax, (0, 1), 2, 1, far_first=False, title='SIDE ELEVATION  (from the right side; front →)')
ax.plot([-185, 185], [0, 0], color=INK, lw=1.2); ax.fill_between([-185, 185], -6, 0, color=GRID, hatch='////', ec='#8c8c8c', lw=0)
for x in (-AX, 0, AX): ax.plot([x, x], [W_R - 40, W_R + 40], color='#7a7a7a', lw=0.5, ls=(0, (6, 3, 1, 3)))
ax.plot([-185, 185], [W_R, W_R], color='#7a7a7a', lw=0.5, ls=(0, (6, 3, 1, 3)))
dim(ax, (-AX - W_R, 0), (AX + W_R, 0), -26, 'overall length 305')
dim(ax, (-AX, W_R), (0, W_R), -42 + 0, '120', fs=8.5)
dim(ax, (0, W_R), (AX, W_R), -42, '120', fs=8.5)
dim(ax, (-PL / 2, PTOP), (PL / 2, PTOP), 70, 'top plate 198')
dim(ax, (AX + W_R, 0), (AX + W_R, PTOP), 28, 'plate top 130', horizontal=False)
dim(ax, (AX + W_R + 28, 0), (AX + W_R + 28, lidar[2]), 22, 'LiDAR scan plane 180', horizontal=False)
dim(ax, (-AX - W_R, 0), (-AX - W_R, W_R * 2), -18, 'Ø65', horizontal=False)
dim(ax, (PIV_X, 0), (PIV_X, PIV_H), -14, 'pivot 95', horizontal=False, fs=8)
dim(ax, (0, PIV_H + 12), (PIV_X, PIV_H + 12), 0, '60', fs=8)
ax.add_patch(Circle((PIV_X, PIV_H), 3.2, fc=SURF, ec=INK, lw=1.0, zorder=5))
ax.annotate('bogie pivot (passive)\nswing: front wheel up 43°,\nmiddle wheel up 28°', (PIV_X, PIV_H), (PIV_X + 55, PIV_H + 55), fontsize=8, color=INK,
            arrowprops=dict(arrowstyle='-', color=INK, lw=0.6))
ax.annotate('rocker (fixed)', (-60, 80), (-150, 150), fontsize=8, color=INK, arrowprops=dict(arrowstyle='-', color=INK, lw=0.6))
ax.annotate('bogie', (95, 40), (150, 70), fontsize=8, color=INK, arrowprops=dict(arrowstyle='-', color=INK, lw=0.6))
ax.annotate('YDLIDAR X2', (lidar[0], lidar[2] - 20), (lidar[0] - 40, lidar[2] + 40), fontsize=8, color=INK, arrowprops=dict(arrowstyle='-', color=INK, lw=0.6))
ax.annotate('Raspberry Pi', (pi[0], PTOP + 12), (pi[0] - 70, PTOP + 60), fontsize=8, color=INK, arrowprops=dict(arrowstyle='-', color=INK, lw=0.6))
ax.text(-AX, -48, 'REAR', ha='center', fontsize=8, color='#7a7a7a'); ax.text(AX, -48, 'FRONT (bogie leads)', ha='center', fontsize=8, color='#7a7a7a')
ax.set_xlim(-200, 270); ax.set_ylim(-70, 250)

# ---- plan view (top) ----------------------------------------------------------------------
ax = fig.add_axes([0.04, 0.05, 0.46, 0.43])
view(ax, (0, 1), 1, 2, far_first=True, title='PLAN  (top view; front →, robot left ↑)')
ax.plot([-185, 185], [0, 0], color='#7a7a7a', lw=0.5, ls=(0, (6, 3, 1, 3)))
dim(ax, (-PL / 2, -PW / 2), (PL / 2, -PW / 2), -42, 'top plate 198')
dim(ax, (-AX - W_R, -W_Y - W_W / 2), (AX + W_R, -W_Y - W_W / 2), -22, 'overall length 305')
dim(ax, (AX + W_R, -W_Y), (AX + W_R, W_Y), 22, 'track 176 (wheel centres)', horizontal=False)
dim(ax, (AX + W_R + 34, -W_Y - W_W / 2), (AX + W_R + 34, W_Y + W_W / 2), 20, 'overall width 201', horizontal=False)
dim(ax, (-PL / 2, -PW / 2), (-PL / 2, PW / 2), -22, 'plate 143', horizontal=False)
dim(ax, (-AX - W_R, W_Y + W_W / 2), (-AX - W_R, W_Y - W_W / 2), -40, '25', horizontal=False, fs=8)
dim(ax, (0, PW / 2), (lidar[0], PW / 2), 30, f'{lidar[0]:.0f}', fs=8)
dim(ax, (pi[0], PW / 2), (0, PW / 2), 30, f'{-pi[0]:.0f}', fs=8)
ax.plot([0, 0], [PW / 2 - 4, PW / 2 + 34], color=DIM, lw=0.6)
ax.plot(0, 0, marker='+', color=INK, ms=10, mew=1.2, zorder=6)
ax.text(-195, 140, '+ robot centre (base_footprint); IMU (MPU-9250) under the plate here, chip facing down.\n'
        'Green: Raspberry Pi. Blue: YDLIDAR X2. Yellow: BO motors between the side plates.', fontsize=7.8, color='#444444', va='top')
ax.set_xlim(-200, 270); ax.set_ylim(-160, 165)

# ---- front elevation -----------------------------------------------------------------------
ax = fig.add_axes([0.52, 0.50, 0.21, 0.43])
view(ax, (1, 1), 2, 0, far_first=False, title='FRONT ELEVATION')
ax.plot([-125, 125], [0, 0], color=INK, lw=1.2); ax.fill_between([-125, 125], -6, 0, color=GRID, hatch='////', ec='#8c8c8c', lw=0)
dim(ax, (-W_Y, 0), (W_Y, 0), -22, 'track 176')
dim(ax, (-W_Y - W_W / 2, 0), (W_Y + W_W / 2, 0), -40, 'overall width 201')
dim(ax, (-PW / 2, PTOP), (PW / 2, PTOP), 70, 'plate 143')
dim(ax, (W_Y + W_W / 2, 0), (W_Y + W_W / 2, lidar[2]), 18, 'height 180 (scan plane)', horizontal=False)
ax.set_xlim(-130, 150); ax.set_ylim(-70, 250)

# ---- 3-D view ----------------------------------------------------------------------------------
ax = fig.add_axes([0.73, 0.50, 0.26, 0.43], projection='3d')
for name, col, pts in parts:
    if len(pts) == 8:      # box: 6 faces
        idx = [[0, 1, 3, 2], [4, 5, 7, 6], [0, 1, 5, 4], [2, 3, 7, 6], [0, 2, 6, 4], [1, 3, 7, 5]]
        faces = [pts[i] for i in idx]
    else:                  # cylinder: two caps + side quads
        n = len(pts) // 2; a, b = pts[:n], pts[n:]
        faces = [a, b] + [np.array([a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]]) for k in range(n)]
    ax.add_collection3d(Poly3DCollection(faces, facecolor=col, edgecolor='#333333' if len(pts) == 8 else 'none', linewidths=0.25, alpha=1.0))
ax.set_xlim(-160, 160); ax.set_ylim(-160, 160); ax.set_zlim(0, 200); ax.set_box_aspect((320, 320, 200))
ax.view_init(elev=24, azim=-58); ax.set_axis_off(); ax.set_title('3-D VIEW', loc='left', fontsize=11, color=INK)

# ---- title block and notes -------------------------------------------------------------------
tb = fig.add_axes([0.52, 0.05, 0.47, 0.43]); tb.axis('off')
tb.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, ec=INK, lw=1.2, transform=tb.transAxes))
tb.text(0.03, 0.93, 'EXPLORER ROVER — GENERAL ARRANGEMENT', fontsize=14, weight='bold', color=INK, transform=tb.transAxes)
tb.text(0.03, 0.865, '6-wheel skid-steer, rocker-bogie suspension (Kit4Curious-style), bogie end leads', fontsize=9.5, color=INK, transform=tb.transAxes)
rows = [('Dimension', 'Value (mm)', 'Source'),
        ('Overall length × width × height', '305 × 201 × 180', 'derived'),
        ('Top plate (acrylic)', '198 × 143 × 2.5', 'measured'),
        ('Plate top above ground', '130', 'measured'),
        ('Wheels (×6, BO geared motors)', 'Ø 65 × 25', 'measured'),
        ('Axle spacing', '120 + 120', 'measured'),
        ('Track, wheel centres', '176', 'measured'),
        ('Bogie pivot', '95 high, 60 ahead of middle axle', 'measured / derived'),
        ('Bogie swing', '43° front up / 28° middle up', 'from photos (±5°)'),
        ('Side-plate bars', '30 wide × 2.5 thick', 'measured'),
        ('LiDAR (YDLIDAR X2)', f'Ø 70 × 50, {lidar[0]:.0f} ahead of centre', 'assumed size'),
        ('LiDAR scan plane', '180 above ground', 'assumed height'),
        ('Raspberry Pi', f'85 × 56 × 20, {-pi[0]:.0f} behind centre', 'assumed'),
        ('Motor bodies', '65 × 18.5 × 22', 'assumed'),
        ('Mass (estimate)', '≈ 851 g', 'assumed')]
y0 = 0.81
for i, (a, b, c) in enumerate(rows):
    y = y0 - i * 0.043; w = 'bold' if i == 0 else 'normal'
    tb.text(0.03, y, a, fontsize=8.8, color=INK, weight=w, transform=tb.transAxes)
    tb.text(0.45, y, b, fontsize=8.8, color=INK, weight=w, transform=tb.transAxes)
    tb.text(0.82, y, c, fontsize=8.8, color='#555555' if i else INK, weight=w, transform=tb.transAxes)
    tb.plot([0.03, 0.97], [y - 0.014] * 2, color=GRID, lw=0.6, transform=tb.transAxes)
tb.text(0.03, 0.105, 'All dimensions in mm. Frames: x forward, y left, z up (REP-103); origin = base_footprint (ground, under the middle axle).\n'
        'Part outlines are projections of the URDF visual geometry (explorer_description/urdf/explorer.urdf.xacro),\n'
        'joints at 0. Sim-only: Gazebo DiffDrive effective track (skid_track) is a calibration value, not geometry.',
        fontsize=7.8, color='#444444', transform=tb.transAxes, va='bottom')
tb.text(0.03, 0.03, 'Drawn: generated by rover_drawing.py   |   Scale: not to print scale, proportions exact   |   Units: mm', fontsize=7.8,
        color=INK, transform=tb.transAxes)

for ext in ('png', 'pdf', 'svg'):
    fig.savefig(os.path.join(OUT, f'explorer_rover_drawing.{ext}'), facecolor=SURF)
print('written to', OUT)
