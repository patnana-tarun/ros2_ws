#!/usr/bin/env python3
"""
Generate a procedural cave for Gazebo Harmonic: meshes, textures, models and worlds.

    python3 generate_cave.py --out DIR [--seed N] [--res 0.05]

`colcon build` runs this automatically (see CMakeLists.txt). Run it by hand with another
--seed to get a cave with the same layout but different rock (useful for training variety),
then launch with world:=DIR/worlds/cave.sdf and GZ_SIM_RESOURCE_PATH=DIR/models.

Output in DIR:
  models/cave_rock/     floor, walls, boulders, stalagmites, puddles (+ collision)
  models/cave_roof/     ceiling and stalactites (visual only)
  worlds/cave.sdf       closed cave, dark, lit by lamps. The ceiling is one-sided: solid
                        from inside, see-through from above, so the GUI can watch the robot.
  worlds/cave_open.sdf  same cave without the roof, in daylight (to watch from above)

How it works: the cave is a 2D signed distance field (negative = open space) built from
hand-placed chambers and tunnels, roughened with noise. Two height fields are derived from
it: the floor/wall surface (rises steeply where the distance becomes positive) and the
ceiling (domes over open space, comes down to meet the walls). Scale is chosen for the
explorer robot (~0.24 m long, LiDAR plane at ~0.18 m).
"""
import argparse
import os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

# ---------------------------------------------------------------- layout (metres) -----
# Robot spawns at (0, 0), the centre of chamber A. Two loops (A-B-C-D, B-C-E) give SLAM
# loop closures; three dead ends test exploration.
CHAMBERS = {  # name: (cx, cy, rx, ry, rotation_rad)
    "A": (0.0, 0.0, 1.6, 1.3, 0.2),
    "B": (5.0, 3.0, 2.2, 1.6, -0.3),
    "C": (10.0, -1.0, 3.0, 2.2, 0.15),
    "D": (5.0, -4.5, 1.6, 1.2, 0.5),
    "E": (14.5, 4.5, 1.8, 1.4, 0.0),
    "F": (15.0, -5.5, 1.4, 1.0, -0.4),
}
TUNNELS = [  # (control points, nominal width)
    ([(0, 0), (2.2, 1.9), (5, 3)], 0.85),
    ([(5, 3), (7.6, 2.6), (10, -1)], 1.0),
    ([(10, -1), (7.6, -3.4), (5, -4.5)], 0.9),
    ([(5, -4.5), (2.4, -3.3), (1.2, -1.6), (0, 0)], 0.75),
    ([(10, -1), (12.6, 1.8), (14.5, 4.5)], 0.9),
    ([(5, 3), (8.2, 5.6), (11.5, 5.9), (14.5, 4.5)], 0.72),
    ([(10, -1), (12.8, -3.8), (15, -5.5)], 0.85),
    ([(5, -4.5), (3.2, -6.4), (0.6, -6.9)], 0.72),
    ([(0, 0), (-2.4, 0.9), (-3.2, 2.7)], 0.75),
]
XMIN, XMAX, YMIN, YMAX = -5.0, 18.0, -8.5, 8.0

ROBOT_CLEARANCE = 0.16    # half the robot's width plus margin, for the connectivity check
WALL_TOP_OPEN = 0.5       # wall height in the roofless world
PUDDLE_Z = 0.004
# Rocks must cross the LiDAR scan plane (0.18 m) near their widest, or the 2D LiDAR can't see
# what the robot hits (user, 2026-09-26: keep every rock at LiDAR level for testing).
ROCK_MIN_HEIGHT = 0.26
SPIKE_COLUMN_Z = 0.24     # stalagmites keep their base width up to here, then taper
COLLISION_Z = 0.12        # visual wall height where the collision wall stands


# ---------------------------------------------------------------- noise ---------------
class Noise:
    """Smooth 2D value noise (cubic-spline interpolated random lattice), wraps every
    `period` lattice cells."""

    def __init__(self, rng, period=256):
        self.grid = rng.random((period, period)) * 2 - 1
        self.coeffs = ndi.spline_filter(self.grid, order=3, mode="grid-wrap")

    def __call__(self, x, y, scale):
        return ndi.map_coordinates(self.coeffs, [np.asarray(y) / scale, np.asarray(x) / scale],
                                   order=3, mode="grid-wrap", prefilter=False)

    def fbm(self, x, y, scale, octaves=4, gain=0.5):
        total, amp, norm = 0.0, 1.0, 0.0
        for o in range(octaves):
            total = total + amp * self(x + 31.7 * o, y - 17.3 * o, scale / 2 ** o)
            norm += amp
            amp *= gain
        return total / norm


def tile_noise(rng, freq, n):
    """Seamlessly tiling noise on an n x n image with `freq` lattice cells per tile."""
    grid = rng.random((freq, freq)) * 2 - 1
    u = np.arange(n) / n * freq
    uu, vv = np.meshgrid(u, u)
    return ndi.map_coordinates(grid, [vv, uu], order=3, mode="grid-wrap")


def tile_fbm(rng, base, octaves, n, gain=0.5):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total = total + amp * tile_noise(rng, base * 2 ** o, n)
        norm += amp
        amp *= gain
    return total / norm


# ---------------------------------------------------------------- cave field ----------
def catmull_rom(points, step):
    p = np.asarray(points, float)
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1:i + 3]
        n = max(int(np.linalg.norm(p2 - p1) / step), 2)
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2][None])
    return np.vstack(out)


def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.minimum(a, b) - h * h * k / 4


def cave_sdf(X, Y, rng, noise):
    pts = np.column_stack([X.ravel(), Y.ravel()])
    sdf = np.full(len(pts), 1e3)

    # Tunnels: meandering centre line with varying width
    samples, half_w = [], []
    for ti, (ctrl, width) in enumerate(TUNNELS):
        c = catmull_rom(ctrl, 0.02)
        seg = np.diff(c, axis=0, append=c[-1:] + (c[-1:] - c[-2:-1]))
        tang = seg / np.linalg.norm(seg, axis=1, keepdims=True)
        normal = np.column_stack([-tang[:, 1], tang[:, 0]])
        s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))])
        taper = np.clip(np.minimum(s, s[-1] - s) / 1.2, 0, 1)  # no meander at the ends
        meander = 0.35 * noise.fbm(s, np.full_like(s, 50.0 + 13 * ti), 2.0, 3) * taper
        samples.append(c + normal * meander[:, None])
        half_w.append(width / 2 * (1 + 0.15 * noise.fbm(s, np.full_like(s, 90.0 + 7 * ti), 1.5, 2)))
    samples, half_w = np.vstack(samples), np.concatenate(half_w)
    dist, idx = cKDTree(samples).query(pts, k=6)
    sdf = np.min(dist - half_w[idx], axis=1)

    # Chambers: ellipses with a wobbly outline, blended smoothly into the tunnels
    for cx, cy, rx, ry, rot in CHAMBERS.values():
        dx, dy = pts[:, 0] - cx, pts[:, 1] - cy
        lx = np.cos(rot) * dx + np.sin(rot) * dy
        ly = -np.sin(rot) * dx + np.cos(rot) * dy
        theta = np.arctan2(ly / ry, lx / rx)
        wobble = 1 + sum(rng.uniform(0.03, 0.09) / np.sqrt(k)
                         * np.sin(k * theta + rng.uniform(0, 2 * np.pi)) for k in range(2, 8))
        r = np.hypot(lx / rx, ly / ry)
        sdf = smin(sdf, (r - wobble) * min(rx, ry), 0.5)

    sdf = sdf.reshape(X.shape)
    # Rough rock: large bulges + small knobbles
    sdf += 0.08 * noise.fbm(X, Y, 0.9, 3) + 0.02 * noise.fbm(X + 100, Y, 0.15, 2)
    return sdf


def heights(X, Y, s, noise):
    """Floor/wall height zf and ceiling height zc from the signed distance s."""
    rock = np.maximum(s, 0)
    depth = np.maximum(-s, 0)
    floor = 0.012 * noise.fbm(X, Y + 200, 0.3, 3) - 0.004
    skirt = 0.035 * np.clip((s + 0.10) / 0.10, 0, 1) ** 2         # rubble along the wall foot
    wall = 1.3 * np.sqrt(rock) + 0.10 * noise.fbm(X + 300, Y, 0.12, 3) * np.clip(rock / 0.08, 0, 1)
    zf = np.where(s < 0, floor + skirt, 0.07 + wall)

    dome = 0.46 + 0.95 * (1 - np.exp(-depth / 0.8)) - 2.2 * rock
    drips = 0.06 * noise.fbm(X, Y + 400, 0.25, 3) + 0.03 * noise.fbm(X + 500, Y, 0.07, 2)
    zc = dome + drips
    # The wall foot rises ~0.3 m within one grid cell; a light blur stops it rendering as a
    # sawtooth. Collision uses the same smoothed surface, so the LiDAR still sees what it hits.
    sigma = 0.05 / (X[0, 1] - X[0, 0])
    return ndi.gaussian_filter(zf, sigma), ndi.gaussian_filter(zc, sigma)


def check_connected(s, res):
    """Every chamber must be reachable from the spawn chamber by the robot."""
    free = s < -ROBOT_CLEARANCE
    labels, _ = ndi.label(free)
    def cell(x, y):
        return labels[int(round((y - YMIN) / res)), int(round((x - XMIN) / res))]
    spawn = cell(0, 0)
    bad = [n for n, (cx, cy, *_) in CHAMBERS.items() if cell(cx, cy) != spawn or spawn == 0]
    if bad:
        raise SystemExit(f"generate_cave: chambers {bad} not reachable from spawn; try another --seed")


# ---------------------------------------------------------------- meshes --------------
class Mesh:
    def __init__(self):
        self.v, self.n, self.f = [], [], []
        self.count = 0

    def add(self, v, n, f):
        self.v.append(v)
        self.n.append(n)
        self.f.append(f + self.count)
        self.count += len(v)

    def arrays(self):
        if not self.v:
            return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros((0, 3), int)
        return np.vstack(self.v), np.vstack(self.n), np.vstack(self.f)


def write_obj(path, v, n, f, uv_scale, vertical=False):
    """OBJ with triplanar UVs: each face is projected along the axis its normal points to
    most, so steep walls don't smear the texture. vertical=True never projects from above
    (for walls: avoids a sawtooth of stretched faces where the wall foot flattens out)."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    fn = np.abs(np.cross(b - a, c - a))
    if vertical:
        fn[:, 2] = 0
    axis = np.argmax(fn, axis=1)                                # 0: x, 1: y, 2: z
    proj = {0: (1, 2), 1: (0, 2), 2: (0, 1)}
    uv_all = np.stack([v[:, proj[k]] / uv_scale for k in range(3)])   # (3, V, 2)
    vt_key = f * 3 + axis[:, None]                              # unique (vertex, axis)
    used, inv = np.unique(vt_key.ravel(), return_inverse=True)
    vt = uv_all[used % 3, used // 3]
    ft = inv.reshape(f.shape)
    with open(path, "w") as fh:
        fh.write("# generated by generate_cave.py\n")
        np.savetxt(fh, v, fmt="v %.4f %.4f %.4f")
        np.savetxt(fh, vt, fmt="vt %.4f %.4f")
        np.savetxt(fh, n, fmt="vn %.3f %.3f %.3f")
        idx = np.stack([f + 1, ft + 1, f + 1], axis=2).reshape(len(f), 9)
        np.savetxt(fh, idx, fmt="f %d/%d/%d %d/%d/%d %d/%d/%d")


def grid_normals(Z, res, sign=1.0):
    gy, gx = np.gradient(Z, res)
    n = np.dstack([-gx, -gy, np.ones_like(Z)]) * sign
    return n / np.linalg.norm(n, axis=2, keepdims=True)


def grid_surface(X, Y, Z, res, cells, flip=False, merge_flat=None, block=8):
    """Triangles for the grid cells in the boolean mask `cells` (shape = Z.shape - 1).
    merge_flat=h replaces fully flat blocks at height h by two large triangles."""
    H, W = Z.shape
    vid = np.arange(H * W).reshape(H, W)
    V = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    N = grid_normals(Z, res, -1.0 if flip else 1.0).reshape(-1, 3)
    cells = cells.copy()
    big = []
    if merge_flat is not None:
        flat = np.isclose(Z, merge_flat)
        for i in range(0, H - block, block):
            for j in range(0, W - block, block):
                if cells[i:i + block, j:j + block].all() and flat[i:i + block + 1, j:j + block + 1].all():
                    cells[i:i + block, j:j + block] = False
                    big.append((vid[i, j], vid[i, j + block], vid[i + block, j + block], vid[i + block, j]))
    ii, jj = np.nonzero(cells)
    q = np.column_stack([vid[ii, jj], vid[ii, jj + 1], vid[ii + 1, jj + 1], vid[ii + 1, jj]])
    # Split each cell along the diagonal with the smaller height change, so steep walls that
    # run at an angle to the grid follow their contour instead of forming a sawtooth
    z = Z.ravel()
    along02 = np.abs(z[q[:, 0]] - z[q[:, 2]]) <= np.abs(z[q[:, 1]] - z[q[:, 3]])
    tris = np.vstack([q[along02][:, [0, 1, 2]], q[along02][:, [0, 2, 3]],
                      q[~along02][:, [0, 1, 3]], q[~along02][:, [1, 2, 3]]])
    if big:
        big = np.array(big)
        tris = np.vstack([tris, big[:, [0, 1, 2]], big[:, [0, 2, 3]]])
    if flip:
        tris = tris[:, ::-1]
    used, inv = np.unique(tris.ravel(), return_inverse=True)
    return V[used], N[used], inv.reshape(tris.shape)


def split_by_slope(v, n, f, floor_mask_fn):
    """Split faces into (floor, wall) meshes."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    fn = np.cross(b - a, c - a)
    fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
    is_floor = floor_mask_fn(fn, (a + b + c) / 3)
    out = []
    for sel in (is_floor, ~is_floor):
        ff = f[sel]
        used, inv = np.unique(ff.ravel(), return_inverse=True)
        out.append((v[used], n[used], inv.reshape(ff.shape)))
    return out


def icosphere(level):
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t),
         (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4),
         (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8),
         (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    v = [np.array(p, float) / np.linalg.norm(p) for p in v]
    for _ in range(level):
        cache, nf = {}, []
        def mid(i, j):
            key = (min(i, j), max(i, j))
            if key not in cache:
                m = v[i] + v[j]
                v.append(m / np.linalg.norm(m))
                cache[key] = len(v) - 1
            return cache[key]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    return np.array(v), np.array(f)


def vertex_normals(v, f):
    n = np.zeros_like(v)
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    for k in range(3):
        np.add.at(n, f[:, k], fn)
    return n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)


def boulder(rng, pos, radius, ground_z):
    v, f = icosphere(2)
    dirs = rng.normal(size=(5, 3))
    r = 1 + sum(rng.uniform(0.05, 0.14) * np.sin(v @ d * rng.uniform(2, 4) + rng.uniform(0, 6)) for d in dirs)
    v = v * r[:, None] * radius * np.array([1, rng.uniform(0.7, 1.0), rng.uniform(0.55, 0.8)])
    ang = rng.uniform(0, 2 * np.pi)
    rot = np.array([[np.cos(ang), -np.sin(ang), 0], [np.sin(ang), np.cos(ang), 0], [0, 0, 1]])
    v = v @ rot.T
    v[:, 2] = np.maximum(v[:, 2], v[:, 2].min() * 0.4)  # flat bottom, sunk into the floor
    v[:, 2] -= v[:, 2].min() + 0.02
    if v[:, 2].max() < ROCK_MIN_HEIGHT:                 # stretch up to LiDAR level
        v[:, 2] = (v[:, 2] + 0.02) * (ROCK_MIN_HEIGHT + 0.02) / (v[:, 2].max() + 0.02) - 0.02
    v += [pos[0], pos[1], ground_z]
    return v, vertex_normals(v, f), f


def spike(rng, base, height, radius, down=False, segs=12, rings=10):
    """Stalagmite (up) or stalactite (down): a wobbly tapered cone. Stalagmites stay a
    column up to SPIKE_COLUMN_Z so the LiDAR plane cuts them at their base width."""
    t = np.linspace(0, 1, rings)
    a = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    phase = rng.uniform(0, 2 * np.pi, 3)
    if down:
        rad = radius * (1 - t) ** 1.4 + 0.004
    else:
        c = min(SPIKE_COLUMN_Z / height, 0.9)
        rad = radius * (0.9 + 0.1 * (1 - np.minimum(t / c, 1))) * \
            (1 - np.clip((t - c) / (1 - c), 0, 1)) ** 1.4 + 0.004
    wob = 1 + 0.15 * np.sin(3 * a[None] + phase[0] + 4 * t[:, None]) + 0.08 * np.sin(5 * a[None] + phase[1])
    lean = rng.normal(0, 0.06, 2) * height
    x = base[0] + rad[:, None] * wob * np.cos(a)[None] + lean[0] * t[:, None] ** 2
    y = base[1] + rad[:, None] * wob * np.sin(a)[None] + lean[1] * t[:, None] ** 2
    z = base[2] + (-1 if down else 1) * height * t[:, None] * np.ones_like(a)[None]
    v = np.column_stack([x.ravel(), y.ravel(), z.ravel()])
    v = np.vstack([v, [x[-1].mean(), y[-1].mean(), z[-1, 0] + (-0.01 if down else 0.01)]])
    tip = len(v) - 1
    f = []
    for r in range(rings - 1):
        for s in range(segs):
            p, q = r * segs + s, r * segs + (s + 1) % segs
            f += [(p, q, q + segs), (p, q + segs, p + segs)]
    for s in range(segs):
        f.append(((rings - 1) * segs + s, (rings - 1) * segs + (s + 1) % segs, tip))
    f = np.array(f)
    if down:
        f = f[:, ::-1]
    return v, vertex_normals(v, f), f


def disk(center, rx, ry, z, rng, segs=28):
    a = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    w = 1 + 0.2 * np.sin(3 * a + rng.uniform(0, 6)) + 0.1 * np.sin(5 * a + rng.uniform(0, 6))
    v = np.column_stack([center[0] + rx * w * np.cos(a), center[1] + ry * w * np.sin(a), np.full(segs, z)])
    v = np.vstack([[center[0], center[1], z], v])
    f = np.array([(0, 1 + i, 1 + (i + 1) % segs) for i in range(segs)])
    return v, np.tile([0, 0, 1.0], (len(v), 1)), f


# ---------------------------------------------------------------- textures ------------
def normal_map(h, strength):
    gy, gx = np.gradient(np.pad(h, 1, mode="wrap"))
    gx, gy = gx[1:-1, 1:-1], gy[1:-1, 1:-1]
    n = np.dstack([-gx * strength, gy * strength, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8))


def save_rgb(path, rgb):
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(path)


def make_textures(tex_dir, rng, n=1024):
    os.makedirs(tex_dir, exist_ok=True)
    # Rock: limestone-like, layered strata, iron stains, fine grain, faint cracks
    base = tile_fbm(rng, 4, 7, n, gain=0.55)
    grain = tile_fbm(rng, 64, 3, n)
    warp = tile_fbm(rng, 3, 3, n)
    v = np.arange(n)[:, None] / n
    strata = np.sin(2 * np.pi * (v * 9 + 0.8 * warp)) * 0.5 + 0.5
    ridged = 1 - np.abs(tile_fbm(rng, 5, 4, n))
    cracks = np.clip((ridged - 0.955) / 0.045, 0, 1)
    stain = np.clip((tile_fbm(rng, 2, 4, n) - 0.2) * 2.5, 0, 1)
    wet = np.clip((tile_fbm(rng, 3, 3, n) + 0.1) * 2, 0, 1)
    t = np.clip(0.5 + 0.7 * base + 0.12 * (strata - 0.5) + 0.12 * grain, 0, 1)[..., None]
    dark, light = np.array([0.24, 0.22, 0.20]), np.array([0.55, 0.51, 0.46])
    rgb = dark + (light - dark) * t
    rgb = rgb * (1 - 0.3 * stain[..., None]) + np.array([0.40, 0.24, 0.12]) * 0.3 * stain[..., None]
    rgb *= (1 - 0.18 * wet)[..., None] * (1 - 0.3 * cracks)[..., None]
    save_rgb(os.path.join(tex_dir, "rock_albedo.png"), rgb)
    normal_map(base + 0.05 * strata + 0.04 * grain - 0.08 * cracks, 14.0).save(
        os.path.join(tex_dir, "rock_normal.png"))

    # Floor: rounded pebbles of mixed size in dirt
    k = 1400
    seeds = rng.random((k, 2))
    radius = rng.uniform(0.35, 1.0, k) ** 1.5 * 0.022
    tiled = np.vstack([seeds + [dx, dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1)])
    uu, vv = np.meshgrid(np.arange(n) / n, np.arange(n) / n)
    d, i = cKDTree(tiled).query(np.column_stack([uu.ravel(), vv.ravel()]), k=3)
    i = i % k
    bump = np.sqrt(np.clip(1 - (d / radius[i]) ** 2, 0, 1)) * radius[i] / 0.022   # hemisphere per pebble
    height = bump.max(axis=1).reshape(n, n)
    which = i[np.arange(len(i)), bump.argmax(axis=1)].reshape(n, n)
    tint = rng.uniform(0.7, 1.25, k)[which]
    dirt = tile_fbm(rng, 8, 6, n)
    rgb = np.array([0.23, 0.20, 0.17]) * (0.85 + 0.35 * dirt)[..., None]
    peb = np.array([0.35, 0.32, 0.28]) * tint[..., None] * (0.75 + 0.25 * height)[..., None]
    cover = np.clip(height * 3, 0, 1)[..., None] * 0.75
    rgb = rgb + (peb - rgb) * cover
    save_rgb(os.path.join(tex_dir, "gravel_albedo.png"), rgb)
    normal_map(height * 0.5 + 0.15 * dirt, 10.0).save(os.path.join(tex_dir, "gravel_normal.png"))


# ---------------------------------------------------------------- SDF text ------------
def material(albedo, normal, roughness, diffuse="1 1 1 1"):
    return f"""<material>
          <diffuse>{diffuse}</diffuse>
          <specular>0.08 0.08 0.08 1</specular>
          <pbr><metal>
            <albedo_map>{albedo}</albedo_map>
            <normal_map>{normal}</normal_map>
            <roughness>{roughness}</roughness>
            <metalness>0.0</metalness>
          </metal></pbr>
        </material>"""


ROCK = ("model://cave_rock/materials/textures/rock_albedo.png",
        "model://cave_rock/materials/textures/rock_normal.png")
GRAVEL = ("model://cave_rock/materials/textures/gravel_albedo.png",
          "model://cave_rock/materials/textures/gravel_normal.png")
WATER = """<material>
          <ambient>0.04 0.035 0.03 1</ambient>
          <diffuse>0.06 0.052 0.045 1</diffuse>
          <specular>0.6 0.6 0.6 1</specular>
          <pbr><metal><roughness>0.15</roughness><metalness>0.0</metalness></metal></pbr>
        </material>"""


def visual(name, mesh_uri, mat):
    return f"""      <visual name="{name}">
        <geometry><mesh><uri>{mesh_uri}</uri></mesh></geometry>
        {mat}
      </visual>
"""


def model_config(name, desc):
    return f"""<?xml version="1.0"?>
<model>
  <name>{name}</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <description>{desc} Generated by generate_cave.py.</description>
</model>
"""


def light(name, x, y, z, rng_m, intensity=1.0):
    return f"""    <light type="point" name="{name}">
      <pose>{x:.2f} {y:.2f} {z:.2f} 0 0 0</pose>
      <diffuse>1.0 0.78 0.55 1</diffuse>
      <specular>0.2 0.16 0.1 1</specular>
      <intensity>{intensity}</intensity>
      <attenuation><range>{rng_m}</range><constant>0.2</constant><linear>0.5</linear><quadratic>0.35</quadratic></attenuation>
      <cast_shadows>false</cast_shadows>
    </light>
"""


WORLD_PLUGINS = """    <physics name="1ms" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-contact-system" name="gz::sim::systems::Contact"/>
"""


# ---------------------------------------------------------------- main ----------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--res", type=float, default=0.05, help="mesh grid spacing (m)")
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    noise = Noise(rng)
    res = args.res

    rock_dir = os.path.join(args.out, "models", "cave_rock")
    roof_dir = os.path.join(args.out, "models", "cave_roof")
    world_dir = os.path.join(args.out, "worlds")
    for d in (os.path.join(rock_dir, "meshes"), os.path.join(roof_dir, "meshes"), world_dir):
        os.makedirs(d, exist_ok=True)

    xs = np.arange(XMIN, XMAX + res / 2, res)
    ys = np.arange(YMIN, YMAX + res / 2, res)
    X, Y = np.meshgrid(xs, ys)
    s = cave_sdf(X, Y, rng, noise)
    check_connected(s, res)
    zf, zc = heights(X, Y, s, noise)

    def cell_any(m):
        return m[:-1, :-1] | m[1:, :-1] | m[:-1, 1:] | m[1:, 1:]

    def cell_all(m):
        return m[:-1, :-1] & m[1:, :-1] & m[:-1, 1:] & m[1:, 1:]

    inside = zc > zf + 0.002                               # below the ceiling = visible from inside
    # One extra ring of cells so ceiling and walls overlap where they meet (no gaps). There the
    # ceiling dips below the wall surface into the rock, hidden, instead of coinciding with it.
    inside_cells = ndi.binary_dilation(cell_any(inside), iterations=1)

    def is_floor(fn, centre):
        return (fn[:, 2] > 0.8) & (centre[:, 2] < 0.1)

    # --- closed cave: floor + walls up to the ceiling line
    fw = grid_surface(X, Y, zf, res, inside_cells)
    floor_c, wall_c = split_by_slope(*fw, is_floor)
    # --- open cave: walls clamped to WALL_TOP_OPEN, everything kept (flat tops merged)
    zf_open = np.minimum(zf, WALL_TOP_OPEN)
    fw_open = grid_surface(X, Y, zf_open, res, np.ones_like(inside_cells), merge_flat=WALL_TOP_OPEN)
    floor_o, wall_o = split_by_slope(*fw_open, is_floor)
    # --- collision: a near-vertical wall where the visual wall reaches COLLISION_Z (the
    #     floor itself is a plane). Following the visual slope instead lets the rocker-bogie
    #     climb the wall foot and flip over.
    zcol = np.clip((zf - COLLISION_Z) / 0.03, 0, 1) * 0.5
    collision = grid_surface(X, Y, zcol, res, cell_any(zcol > 0) & cell_any(zcol < 0.5))
    # --- ceiling (faces down)
    ceiling = grid_surface(X, Y, zc, res, inside_cells, flip=True)

    for name, m in (("floor", floor_c), ("walls", wall_c), ("floor_open", floor_o),
                    ("walls_open", wall_o), ("collision", collision)):
        write_obj(os.path.join(rock_dir, "meshes", name + ".obj"), *m,
                  uv_scale={"floor": 0.6, "floor_open": 0.6, "walls_open": 2.0}.get(name, 1.0),
                  vertical=(name == "walls"))
    write_obj(os.path.join(roof_dir, "meshes", "ceiling.obj"), *ceiling, uv_scale=1.0)

    # --- formations: boulders + stalagmites (collide), stalactites (roof), puddles
    def sample(x, y):
        i = int(round((y - YMIN) / res))
        j = int(round((x - XMIN) / res))
        return s[i, j], zf[i, j], zc[i, j]

    def in_chamber(p, name):
        """Inside the chamber's ellipse (not the tunnels that leave it)."""
        cx, cy, rx, ry, rot = CHAMBERS[name]
        dx, dy = p[0] - cx, p[1] - cy
        lx = np.cos(rot) * dx + np.sin(rot) * dy
        ly = -np.sin(rot) * dx + np.cos(rot) * dy
        return (lx / rx) ** 2 + (ly / ry) ** 2 < 0.9

    form, drips, puddles = Mesh(), Mesh(), Mesh()
    placed = []
    def free_spot(min_depth, max_depth, avoid):
        for _ in range(400):
            name = rng.choice(list("BCDEF"))
            cx, cy, rx, ry, _ = CHAMBERS[name]
            p = np.array([cx, cy]) + rng.uniform(-1, 1, 2) * [rx, ry]
            d = -sample(*p)[0]
            if not in_chamber(p, name):     # the bounding box reaches into tunnels
                continue
            if min_depth < d < max_depth and np.hypot(*p) > 2.0 and \
                    all(np.linalg.norm(p - q) > avoid for q in placed):
                placed.append(p)
                return p
        return None

    for _ in range(14):                                     # boulders in the chambers
        p = free_spot(0.35, 9, 0.7)
        if p is not None:
            form.add(*boulder(rng, p, rng.uniform(0.12, 0.28), 0.0))
    for _ in range(26):                                     # stalagmites near chamber walls
        p = free_spot(0.12, 0.45, 0.25)
        if p is not None:
            form.add(*spike(rng, (p[0], p[1], -0.01), rng.uniform(0.32, 0.55), rng.uniform(0.04, 0.08)))
    for _ in range(90):                                     # stalactites under high ceiling
        name = rng.choice(list("ABCDEF"))
        cx, cy, rx, ry, _ = CHAMBERS[name]
        p = np.array([cx, cy]) + rng.uniform(-1, 1, 2) * [rx, ry]
        sd, _, z = sample(*p)
        length = rng.uniform(0.08, 0.35)
        if sd < -0.1 and z - length > 0.55:
            drips.add(*spike(rng, (p[0], p[1], z + 0.03), length + 0.03, rng.uniform(0.02, 0.05), down=True))
    for _ in range(6):                                      # puddles in floor hollows
        p = free_spot(0.4, 9, 0.9)
        if p is not None:
            puddles.add(*disk(p, rng.uniform(0.25, 0.6), rng.uniform(0.2, 0.45), PUDDLE_Z, rng))
    write_obj(os.path.join(rock_dir, "meshes", "formations.obj"), *form.arrays(), uv_scale=0.8)
    write_obj(os.path.join(rock_dir, "meshes", "puddles.obj"), *puddles.arrays(), uv_scale=1.0)
    write_obj(os.path.join(roof_dir, "meshes", "stalactites.obj"), *drips.arrays(), uv_scale=0.8)

    make_textures(os.path.join(rock_dir, "materials", "textures"), rng)

    # --- models
    M = "model://cave_rock/meshes/"
    rock_sdf = f"""<?xml version="1.0"?>
<sdf version="1.9">
  <model name="cave_rock">
    <static>true</static>
    <link name="rock">
      <collision name="ground">
        <geometry><plane><normal>0 0 1</normal><size>{XMAX - XMIN + 2} {YMAX - YMIN + 2}</size></plane></geometry>
        <pose>{(XMIN + XMAX) / 2:.2f} {(YMIN + YMAX) / 2:.2f} 0 0 0 0</pose>
        <surface><friction><ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction></surface>
      </collision>
      <collision name="walls">
        <geometry><mesh><uri>{M}collision.obj</uri></mesh></geometry>
      </collision>
      <collision name="formations">
        <geometry><mesh><uri>{M}formations.obj</uri></mesh></geometry>
      </collision>
{visual("floor", M + "floor.obj", material(*GRAVEL, 0.95))}{visual("walls", M + "walls.obj", material(*ROCK, 0.85))}{visual("formations", M + "formations.obj", material(*ROCK, 0.6, "0.9 0.88 0.85 1"))}{visual("puddles", M + "puddles.obj", WATER)}    </link>
  </model>
</sdf>
"""
    # The roofless variant shares the model but swaps the wall meshes
    open_sdf = rock_sdf.replace('name="cave_rock"', 'name="cave_rock_open"') \
        .replace("floor.obj", "floor_open.obj").replace("walls.obj", "walls_open.obj")
    R = "model://cave_roof/meshes/"
    roof_sdf = f"""<?xml version="1.0"?>
<sdf version="1.9">
  <model name="cave_roof">
    <static>true</static>
    <link name="roof">
{visual("ceiling", R + "ceiling.obj", material(*ROCK, 0.7, "0.75 0.73 0.7 1"))}{visual("stalactites", R + "stalactites.obj", material(*ROCK, 0.4, "0.95 0.92 0.85 1"))}    </link>
  </model>
</sdf>
"""
    with open(os.path.join(rock_dir, "model.sdf"), "w") as fh:
        fh.write(rock_sdf)
    with open(os.path.join(rock_dir, "model.config"), "w") as fh:
        fh.write(model_config("cave_rock", "Cave floor, walls and formations."))
    open_dir = os.path.join(args.out, "models", "cave_rock_open")
    os.makedirs(open_dir, exist_ok=True)
    with open(os.path.join(open_dir, "model.sdf"), "w") as fh:
        fh.write(open_sdf)
    with open(os.path.join(open_dir, "model.config"), "w") as fh:
        fh.write(model_config("cave_rock_open", "Roofless cave (walls cut at %.1f m)." % WALL_TOP_OPEN))
    with open(os.path.join(roof_dir, "model.sdf"), "w") as fh:
        fh.write(roof_sdf)
    with open(os.path.join(roof_dir, "model.config"), "w") as fh:
        fh.write(model_config("cave_roof", "Cave ceiling and stalactites."))

    # --- worlds
    lamps = ""
    for name, (cx, cy, rx, ry, _) in CHAMBERS.items():
        _, _, z = sample(cx, cy)
        lamps += light(f"lamp_{name}", cx, cy, 0.75 * z, max(rx, ry) * 2.5, 1.5)
    for k, (ctrl, _) in enumerate(TUNNELS):
        c = catmull_rom(ctrl, 0.05)
        x, y = c[len(c) // 2]
        _, _, z = sample(x, y)
        lamps += light(f"lamp_t{k}", x, y, max(0.3, 0.7 * z), 2.5, 0.6)

    closed = f"""<?xml version="1.0"?>
<!-- Closed cave for the explorer robot. Generated by generate_cave.py (seed {args.seed}).
     Spawn point: (0, 0), centre of the first chamber. -->
<sdf version="1.9">
  <world name="cave">
{WORLD_PLUGINS}    <scene>
      <ambient>0.07 0.07 0.08 1</ambient>
      <background>0 0 0 1</background>
      <shadows>false</shadows>
      <grid>false</grid>
    </scene>
{lamps}    <include><uri>model://cave_rock</uri></include>
    <include><uri>model://cave_roof</uri></include>
  </world>
</sdf>
"""
    opened = f"""<?xml version="1.0"?>
<!-- Roofless version of cave.sdf, in daylight, for watching the robot from above.
     Same layout and collision as cave.sdf. Generated by generate_cave.py (seed {args.seed}). -->
<sdf version="1.9">
  <world name="cave_open">
{WORLD_PLUGINS}    <scene>
      <ambient>0.35 0.35 0.35 1</ambient>
      <background>0.6 0.7 0.8 1</background>
      <shadows>true</shadows>
      <grid>false</grid>
    </scene>
    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.85 0.83 0.8 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.4 0.25 -0.9</direction>
    </light>
    <include><uri>model://cave_rock_open</uri></include>
  </world>
</sdf>
"""
    with open(os.path.join(world_dir, "cave.sdf"), "w") as fh:
        fh.write(closed)
    with open(os.path.join(world_dir, "cave_open.sdf"), "w") as fh:
        fh.write(opened)

    tris = {n: len(m[2]) for n, m in (("floor", floor_c), ("walls", wall_c), ("ceiling", ceiling),
                                      ("collision", collision), ("floor_open", floor_o), ("walls_open", wall_o))}
    print(f"generate_cave: seed {args.seed}, grid {X.shape[1]}x{X.shape[0]} @ {res} m, triangles {tris}")


if __name__ == "__main__":
    main()
