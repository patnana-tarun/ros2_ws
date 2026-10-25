"""Coverage ceiling (nav-speed 2026-10-21; usage: ceiling.py RADIUS [OUT.npz]): share of the true floor a LiDAR can see from poses a robot_radius-R planner can reach."""
import glob, os, sys, numpy as np
from scipy import ndimage as ndi
R = float(sys.argv[1]) if len(sys.argv) > 1 else 0.22
f = np.load('/home/shadows/ros2_ws/data/demo_runs_2026-10-19/field.npz')
s, res, x0, y0 = f['s'], float(f['res']), float(f['XMIN']), float(f['YMIN'])
F = s < 0
H, W = F.shape
yy, xx = np.mgrid[0:H, 0:W]; X = x0 + xx * res; Y = y0 + yy * res
B = [(9.55,-0.16,.18),(7.64,-0.47,.18),(4.72,4.17,.20),(5.99,3.69,.15),(10.33,-2.26,.12),(15.05,4.05,.24),
     (6.38,2.70,.27),(14.09,-4.69,.12),(15.72,-5.79,.28),(3.70,2.52,.28),(4.03,3.54,.21),(10.74,-0.63,.18),(15.49,5.24,.18)]
rock = np.zeros_like(F)
for bx, by, r in B: rock |= np.hypot(X - bx, Y - by) < r
# stalagmites etc.: occupied in >= 2 final maps, inside the floor, away from walls
maps = sorted(glob.glob('/home/shadows/tunnelrev_runs_2026-10-20/**/*_map.npz', recursive=True) +
              glob.glob('/home/shadows/ros2_ws/data/demo_runs_2026-10-19/*_map.npz'))
occ_n = np.zeros(F.shape, int); known_any = np.zeros(F.shape, bool); per = {}
for m in maps:
    d = np.load(m); a = d['data']; ox, oy, r_ = float(d['ox']), float(d['oy']), float(d['res'])
    iy, ix = np.nonzero(a >= 0)
    gi = np.floor((oy + (iy + .5) * r_ - y0) / res + .5).astype(int); gj = np.floor((ox + (ix + .5) * r_ - x0) / res + .5).astype(int)
    ok = (gi >= 0) & (gi < H) & (gj >= 0) & (gj < W)
    k = np.zeros(F.shape, bool); k[gi[ok], gj[ok]] = True
    o = np.zeros(F.shape, bool); sel = ok & (a[iy, ix] >= 65); o[gi[sel], gj[sel]] = True
    occ_n += o; known_any |= k; per[m.split('/')[-1][:-8]] = k
import json
stal = np.zeros_like(F)
for sx, sy, sh, sr in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stalagmites.json'))): stal |= np.hypot(X - sx, Y - sy) < sr
O = ~F | rock | stal
dist = ndi.distance_transform_edt(~O) * res
free = dist > R
lab, _ = ndi.label(free)
c0 = lab[int(round((0 - y0) / res)), int(round((0 - x0) / res))]
reach = lab == c0
# raycast from reachable cells (every 2nd cell), 7.5 m, 1080 rays
src = np.argwhere(reach)[::1]
src = src[(src[:, 0] % 2 == 0) & (src[:, 1] % 2 == 0)]
ang = np.linspace(0, 2 * np.pi, 1080, endpoint=False); steps = np.arange(1, int(7.5 / (res * 0.5))) * 0.5
dx, dy = np.cos(ang)[:, None] * steps, np.sin(ang)[:, None] * steps
seen = np.zeros(F.shape, bool)
for i, j in src:
    pi = np.clip(np.round(i + dy).astype(int), 0, H - 1); pj = np.clip(np.round(j + dx).astype(int), 0, W - 1)
    blk = O[pi, pj]
    first = np.where(blk.any(1), blk.argmax(1), blk.shape[1] - 1)
    mask = np.arange(blk.shape[1])[None, :] <= first[:, None]
    seen[pi[mask], pj[mask]] = True
floor_m2 = F.sum() * res**2
print(f'R={R}: floor {floor_m2:.1f} m2; rocks {rock.sum()*res**2:.2f} m2, stalagmite cells {stal.sum()*res**2:.2f} m2')
print(f'reachable centre cells {reach.sum()*res**2:.1f} m2 ({100*reach.sum()/F.sum():.1f} % of floor)')
print(f'CEILING (LiDAR-visible floor from reachable poses): {100*(seen & F).sum()/F.sum():.1f} %')
print(f'  rock interiors unseeable: {100*(F & ~seen & (rock|stal)).sum()/F.sum():.1f} %')
print(f'empirical union of {len(maps)} final maps: {100*(known_any & F).sum()/F.sum():.1f} %')
for k, v in per.items(): print(f'  {k}: {100*(v & F).sum()/F.sum():.1f} %')
miss = F & ~seen
lab2, n2 = ndi.label(miss)
sz = ndi.sum(miss, lab2, range(1, n2 + 1)) * res**2
for idx in np.argsort(sz)[::-1][:8]:
    cy, cx = ndi.center_of_mass(lab2 == idx + 1)
    print(f'  unseen blob {sz[idx]:.2f} m2 at ({x0+cx*res:.1f}, {y0+cy*res:.1f})')
np.savez_compressed(sys.argv[2] if len(sys.argv) > 2 else 'ceiling.npz', seen=seen, reach=reach, F=F, O=O, known_any=known_any)
