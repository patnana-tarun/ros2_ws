"""
Clearance grid for cave.sdf (2026-10-25, user's request: start the demo from a random or a chosen
place instead of always (0, 0)). Writes config/cave_clearance.npz, which spawn_point reads.

Each 0.1 m cell holds its distance (cm) to the nearest wall, boulder or stalagmite (same obstacle
model as docs/assets/navigation/nav-speed/ceiling.py), and 0 where the cell is rock or cannot be
reached from (0, 0) by a planner of radius 0.22 m. The floor at every cell with >= 0.3 m clearance
is within 2 cm of z = 0 (checked 2026-10-25), so the spawn height stays 0.02 m.

    python3 src/explorer_exploration/scripts/make_cave_clearance.py      # then colcon build
"""
import json
import os

import numpy as np
from scipy import ndimage as ndi

WS = os.path.expanduser('~/ros2_ws')
FIELD = os.path.join(WS, 'data/demo_runs_2026-10-19/field.npz')
STALAGMITES = os.path.join(WS, 'docs/assets/navigation/nav-speed/stalagmites.json')
OUT = os.path.join(WS, 'src/explorer_exploration/config/cave_clearance.npz')
# boulders (x, y, r) as the cave generator places them (seed 7), from ceiling.py
BOULDERS = [(9.55, -0.16, .18), (7.64, -0.47, .18), (4.72, 4.17, .20), (5.99, 3.69, .15),
            (10.33, -2.26, .12), (15.05, 4.05, .24), (6.38, 2.70, .27), (14.09, -4.69, .12),
            (15.72, -5.79, .28), (3.70, 2.52, .28), (4.03, 3.54, .21), (10.74, -0.63, .18),
            (15.49, 5.24, .18)]
PLANNER_R = 0.22
STEP = 2          # 0.05 m field cells -> 0.1 m

f = np.load(FIELD)
s, zf, res, x0, y0 = f['s'], f['zf'], float(f['res']), float(f['XMIN']), float(f['YMIN'])
H, W = s.shape
yy, xx = np.mgrid[0:H, 0:W]
X, Y = x0 + xx * res, y0 + yy * res
obst = s >= 0
for bx, by, r in BOULDERS:
    obst |= np.hypot(X - bx, Y - by) < r
for sx, sy, _h, r in json.load(open(STALAGMITES)):
    obst |= np.hypot(X - sx, Y - sy) < r
dist = ndi.distance_transform_edt(~obst) * res
lab, _ = ndi.label(dist > PLANNER_R)
reach = lab == lab[int(round(-y0 / res)), int(round(-x0 / res))]
clear = np.where(reach, dist, 0.0)[::STEP, ::STEP]
floor_z = np.abs(zf[reach & (dist >= 0.3)]).max()
assert floor_z < 0.02, f'floor up to {floor_z:.3f} m: the spawn height needs a z argument'
np.savez_compressed(OUT, clear_cm=np.clip(np.round(clear * 100), 0, 255).astype(np.uint8),
                    res=res * STEP, x0=x0, y0=y0, world='cave.sdf')
print(f'{clear.shape[1]} x {clear.shape[0]} cells, {(clear >= 0.6).sum()} with >= 0.6 m clearance, '
      f'floor |z| <= {floor_z:.3f} m -> {OUT}')
