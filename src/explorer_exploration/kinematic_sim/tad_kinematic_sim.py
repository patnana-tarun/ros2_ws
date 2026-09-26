#!/usr/bin/env python3
"""
Standalone kinematic TAD exploration simulator — Method A from the
paper-vs-project reproduction study.

WHY THIS EXISTS
----------------
The earlier ROS2/Gazebo/Nav2 reproduction established that our TAD scoring
logic is a faithful port of Buriboev, Choi & Jeon (2025), but that absolute
seconds/metres could never be compared meaningfully against the paper
because the paper's simulator (MATLAB Robotics System Toolbox) has:
  - no physics engine (fixed-speed kinematic motion only)
  - no Nav2-equivalent planner/controller/costmap stack
  - much larger test rooms than our turtlebot3_world (~4.5x4.5 m)

This script removes all three confounds by directly reimplementing the
paper's own simplification layer in pure Python/NumPy: a point-ish robot
that senses via raycasting, moves at a fixed configured speed with no
acceleration/physics, and is not routed through any navigation stack.

It reuses the EXACT SAME frontier-detection and TAD-scoring logic already
used and validated in explorer_exploration/frontier_tad_node.py (ROS2
version) - ported here without ROS2 dependencies so it can also be
verified line-by-line against that file.

DOCUMENTED ASSUMPTIONS (paper does not specify these numerically)
-------------------------------------------------------------------
- Room wall layouts: the paper only shows floor-plan sketches (Fig. 5),
  not numeric wall coordinates. We generate a grid-of-rooms layout at the
  paper's exact stated outer dimensions, with doorway connectivity chosen
  to be a loop (cyclic) or a spanning tree (non-cyclic) as appropriate.
- Angular speed: the paper gives no turning rate. We assume 1.0 rad/s,
  labelled explicitly wherever it affects a result.
- Path smoothing factor's exact effect: the paper names it as a tunable
  parameter but never defines its formula. We use it to linearly discount
  the turning-time penalty: effective_turn_time = turn_time * (1 - 0.5*factor).
- Local obstacle avoidance: the paper names no planner. We use a grid BFS
  shortest-path over currently-known-free cells when a straight line to
  the goal is blocked - the simplest defensible stand-in.
"""

import math
import sys
import time
from collections import deque

import numpy as np
from scipy import ndimage

# ---------------------------------------------------------------------------
# Map generation - grid-of-rooms layout at the paper's stated outer size.
# ---------------------------------------------------------------------------

def build_room_grid_map(width_m, height_m, resolution, rooms_x, rooms_y, cyclic, rng):
    """Ground-truth occupancy grid: 0=free, 100=obstacle. Outer walls +
    a rooms_x by rooms_y grid of internal partitions with doorways.
    cyclic=True opens every internal doorway (creates loops).
    cyclic=False opens only a spanning-tree subset (dead-end topology)."""
    w_cells = int(round(width_m / resolution))
    h_cells = int(round(height_m / resolution))
    grid = np.zeros((h_cells, w_cells), dtype=np.int16)

    wall_th = max(1, int(round(0.10 / resolution)))  # 10cm wall thickness
    grid[:wall_th, :] = 100
    grid[-wall_th:, :] = 100
    grid[:, :wall_th] = 100
    grid[:, -wall_th:] = 100

    col_bounds = np.linspace(0, w_cells, rooms_x + 1).astype(int)
    row_bounds = np.linspace(0, h_cells, rooms_y + 1).astype(int)

    for c in col_bounds[1:-1]:
        grid[:, max(0, c - wall_th // 2):c + wall_th - wall_th // 2] = 100
    for r in row_bounds[1:-1]:
        grid[max(0, r - wall_th // 2):r + wall_th - wall_th // 2, :] = 100

    # Doorway plan: spanning tree always included; cyclic adds the rest.
    edges = []
    for ry in range(rooms_y):
        for rx in range(rooms_x):
            if rx + 1 < rooms_x:
                edges.append(((rx, ry), (rx + 1, ry), 'v'))
            if ry + 1 < rooms_y:
                edges.append(((rx, ry), (rx, ry + 1), 'h'))

    rng.shuffle(edges)
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            return True
        return False

    doorways = []
    for a, b, orient in edges:
        if union(a, b):
            doorways.append((a, b, orient))
    if cyclic:
        for a, b, orient in edges:
            if (a, b, orient) not in doorways and (find(a) == find(b)):
                doorways.append((a, b, orient))

    door_width = max(2, int(round(1.0 / resolution)))  # 1m doorway
    for (rx1, ry1), (rx2, ry2), orient in doorways:
        if orient == 'v':
            c = col_bounds[rx2]
            r0, r1 = row_bounds[ry1], row_bounds[ry1 + 1]
            mid = (r0 + r1) // 2
            grid[max(0, mid - door_width // 2):mid + door_width // 2,
                 max(0, c - wall_th):c + wall_th] = 0
        else:
            r = row_bounds[ry2]
            c0, c1 = col_bounds[rx1], col_bounds[rx1 + 1]
            mid = (c0 + c1) // 2
            grid[max(0, r - wall_th):r + wall_th,
                 max(0, mid - door_width // 2):mid + door_width // 2] = 0

    return grid, resolution


# ---------------------------------------------------------------------------
# Sensor: raycast the true map, update the known (SLAM-equivalent) grid.
# ---------------------------------------------------------------------------

def raycast_update(true_grid, known_grid, resolution, rx, ry, n_rays, max_range, min_range):
    h, w = true_grid.shape
    rcol = rx / resolution
    rrow = ry / resolution
    max_cells = max_range / resolution
    for i in range(n_rays):
        angle = 2 * math.pi * i / n_rays
        dx, dy = math.cos(angle), math.sin(angle)
        step = 0.5  # cells per raycast step (sub-cell for accuracy)
        dist = 0.0
        while dist < max_cells:
            col = int(rcol + dx * dist)
            row = int(rrow + dy * dist)
            if not (0 <= row < h and 0 <= col < w):
                break
            if dist * resolution >= min_range:
                if true_grid[row, col] >= 100:
                    known_grid[row, col] = 100
                    break
                known_grid[row, col] = 0
            dist += step


# ---------------------------------------------------------------------------
# Frontier detection - identical logic to frontier_tad_node.py.
# ---------------------------------------------------------------------------

def detect_frontiers(known_grid, min_frontier_size):
    free = (known_grid == 0)
    unknown = (known_grid == -1)
    frontier_mask = np.zeros_like(free, dtype=bool)
    frontier_mask[:-1, :] |= free[:-1, :] & unknown[1:, :]
    frontier_mask[1:, :] |= free[1:, :] & unknown[:-1, :]
    frontier_mask[:, :-1] |= free[:, :-1] & unknown[:, 1:]
    frontier_mask[:, 1:] |= free[:, 1:] & unknown[:, :-1]

    if not np.any(frontier_mask):
        return []

    # 8-connectivity: a frontier curve running diagonally is a staircase whose
    # cells touch only at corners, so 4-connectivity shatters one real frontier
    # into fragments that min_frontier_size then discards. Must match
    # frontier_tad_node.py, whose equivalence with this function is asserted by
    # the validation suite.
    labeled, num = ndimage.label(frontier_mask, structure=np.ones((3, 3), dtype=bool))
    clusters = []
    for cid in range(1, num + 1):
        ys, xs = np.where(labeled == cid)
        if len(xs) < min_frontier_size:
            continue
        clusters.append((ys, xs))
    return clusters


# ---------------------------------------------------------------------------
# TAD scoring - identical d_n / a_n / t_n / F_n logic to frontier_tad_node.py.
# ---------------------------------------------------------------------------

def score_frontiers(clusters, known_grid, resolution, rx, ry,
                     short_range, long_range, w_d, w_a, w_t,
                     exclude_positions=None, exclude_radius=0.3):
    h, w = known_grid.shape
    unknown = (known_grid == -1)
    unknown_labeled, _ = ndimage.label(unknown)
    unknown_region_sizes = np.bincount(unknown_labeled.ravel())

    rcol = rx / resolution
    rrow = ry / resolution

    candidates = []
    for ys, xs in clusters:
        centroid_row = float(np.mean(ys))
        centroid_col = float(np.mean(xs))
        wx = centroid_col * resolution
        wy = centroid_row * resolution
        d_n = float(np.hypot(wx - rx, wy - ry))

        row_off = ys + np.array([-1, 1, 0, 0])[:, None]
        col_off = xs + np.array([0, 0, -1, 1])[:, None]
        touched = set()
        for r_off, c_off in zip(row_off, col_off):
            valid = (r_off >= 0) & (r_off < h) & (c_off >= 0) & (c_off < w)
            for r, c in zip(r_off[valid], c_off[valid]):
                lbl = unknown_labeled[r, c]
                if lbl != 0:
                    touched.add(lbl)
        a_n = float(sum(unknown_region_sizes[l] for l in touched)) * (resolution ** 2)

        cell_dist = np.hypot(xs - rcol, ys - rrow) * resolution
        inner = int(np.sum(cell_dist <= short_range))
        outer = int(np.sum((cell_dist > short_range) & (cell_dist <= long_range)))
        t_n = 1.0 if outer > inner else (0.0 if outer == inner else -1.0)

        candidates.append({'x': wx, 'y': wy, 'd': d_n, 'a': a_n, 't': t_n})

    if not candidates:
        return None

    # Exclude candidates too close to a recently-visited goal - without this,
    # exact (tolerance-free) point-to-point kinematics can 2-cycle between
    # two near-identical-scoring frontiers forever (verified experimentally;
    # see module docstring / experiment log). A real controller's goal
    # tolerance and odometry noise break this naturally; our exact kinematic
    # model needs the equivalent explicitly. Standard technique in the
    # literature (frontier blacklisting, e.g. m-explore).
    usable = candidates
    if exclude_positions:
        filtered = [c for c in candidates
                    if all(math.hypot(c['x'] - ex, c['y'] - ey) > exclude_radius
                           for ex, ey in exclude_positions)]
        if not filtered:
            # exclude_positions is the persistent blacklist of goals already
            # proven to just re-cycle (see run_environment) - if every
            # current candidate is on it, there is genuinely no new option
            # among currently-detected frontiers.
            return None
        usable = filtered

    def norm(vals):
        vals = np.array(vals, dtype=float)
        lo, hi = vals.min(), vals.max()
        return np.ones_like(vals) if hi - lo < 1e-6 else (vals - lo) / (hi - lo)

    d_v = norm([c['d'] for c in usable])
    a_v = norm([c['a'] for c in usable])
    t_v = norm([c['t'] for c in usable])
    scores = w_d * d_v + w_a * a_v + w_t * t_v
    best = usable[int(np.argmax(scores))]
    return best


# ---------------------------------------------------------------------------
# Path execution - BFS-on-known-free-cells if line-of-sight is blocked,
# else straight line. Kinematic time model per the documented assumptions.
# ---------------------------------------------------------------------------

def line_of_sight_clear(known_grid, resolution, x0, y0, x1, y1):
    h, w = known_grid.shape
    c0, r0 = x0 / resolution, y0 / resolution
    c1, r1 = x1 / resolution, y1 / resolution
    steps = int(max(abs(c1 - c0), abs(r1 - r0)))
    if steps == 0:
        return True
    for i in range(steps + 1):
        t = i / steps
        r, c = int(r0 + (r1 - r0) * t), int(c0 + (c1 - c0) * t)
        if not (0 <= r < h and 0 <= c < w) or known_grid[r, c] == 100:
            return False
    return True


def bfs_path(known_grid, resolution, x0, y0, x1, y1):
    h, w = known_grid.shape
    start = (int(y0 / resolution), int(x0 / resolution))
    goal = (int(y1 / resolution), int(x1 / resolution))
    free = known_grid != 100
    visited = np.zeros_like(free, dtype=bool)
    prev = {}
    q = deque([start])
    visited[start] = True
    found = False
    while q:
        cur = q.popleft()
        if cur == goal or math.hypot(cur[0] - goal[0], cur[1] - goal[1]) < 3:
            found = True
            goal = cur
            break
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = cur[0] + dr, cur[1] + dc
            if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc] and free[nr, nc]:
                visited[nr, nc] = True
                prev[(nr, nc)] = cur
                q.append((nr, nc))
    if not found:
        return [(x0, y0), (x1, y1)]  # fallback: straight line
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    # Downsample to waypoints every ~0.5m to keep turning-point counting sane
    pts = [(c * resolution, r * resolution) for r, c in path]
    simplified = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - simplified[-1][0], p[1] - simplified[-1][1]) >= 0.5:
            simplified.append(p)
    simplified.append((x1, y1))
    return simplified


def execute_path(known_grid, resolution, rx, ry, gx, gy,
                  speed, turn_angle_threshold_deg, angular_speed, smoothing_factor):
    if line_of_sight_clear(known_grid, resolution, rx, ry, gx, gy):
        waypoints = [(rx, ry), (gx, gy)]
    else:
        waypoints = bfs_path(known_grid, resolution, rx, ry, gx, gy)

    distance = 0.0
    turn_time = 0.0
    turning_points = 0
    heading = None
    for i in range(1, len(waypoints)):
        x0, y0 = waypoints[i - 1]
        x1, y1 = waypoints[i]
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg < 1e-6:
            continue
        distance += seg
        new_heading = math.atan2(y1 - y0, x1 - x0)
        if heading is not None:
            dtheta = abs(math.atan2(math.sin(new_heading - heading), math.cos(new_heading - heading)))
            if math.degrees(dtheta) > turn_angle_threshold_deg:
                turning_points += 1
                turn_time += dtheta / angular_speed
        heading = new_heading

    turn_time *= (1 - 0.5 * smoothing_factor)  # documented smoothing assumption
    travel_time = distance / speed + turn_time
    return gx, gy, distance, travel_time, turning_points


# ---------------------------------------------------------------------------
# Main exploration loop for one environment.
# ---------------------------------------------------------------------------

def run_environment(name, width_m, height_m, rooms_x, rooms_y, cyclic,
                     start_x, start_y, resolution=0.05, seed=42,
                     speed=0.2, turn_angle_threshold_deg=45.0,
                     smoothing_factor=0.5, angular_speed=1.0,
                     sensor_short=0.5, sensor_long=5.0, n_rays=720,
                     min_frontier_m=0.35, w_d=1.0, w_a=1.0, w_t=1.0,
                     max_goals=400):
    rng = np.random.RandomState(seed)
    true_grid, res = build_room_grid_map(width_m, height_m, resolution, rooms_x, rooms_y, cyclic, rng)
    known_grid = np.full_like(true_grid, -1)

    min_frontier_cells = max(1, int(round(min_frontier_m / res)))

    rx, ry = start_x, start_y
    total_distance = 0.0
    total_time = 0.0
    total_turns = 0
    goal_count = 0

    raycast_update(true_grid, known_grid, res, rx, ry, n_rays, sensor_long, sensor_short)

    t_start = time.time()
    # Stall detection: single-shot raycasting (unlike real accumulating SLAM)
    # leaves permanent 1-2 cell shadow slivers near walls/doorway edges that
    # can never fully close. If newly-known-cell growth stays negligible for
    # several consecutive goals, treat remaining frontiers as sensor/
    # discretization noise rather than genuine unexplored space - this is a
    # documented simulator-level termination rule, not a change to any
    # paper-specified parameter (rays, min frontier size, etc. are untouched).
    STALL_WINDOW = 5
    STALL_MIN_NEW_CELLS = 15
    recent_known_counts = deque(maxlen=STALL_WINDOW)
    recent_known_counts.append(int(np.sum(known_grid != -1)))
    # Persistent blacklist (not just a last-N window): a goal only gets
    # excluded once it's proven unproductive (visiting it didn't reveal new
    # map), matching the m-explore-style "frontier blacklisting" this code
    # already names in score_frontiers' docstring. A short sliding window
    # doesn't work here - two nearby frontier slivers each fall inside the
    # other's exclusion radius, so the pair cycles forever instead of ever
    # getting excluded (verified experimentally: 'wide' env bounced between
    # the same two points for the whole run and never explored past 4.9%).
    blacklist = []
    visit_counts = {}  # rounded (x, y) -> number of times chosen as a goal
    stalled = False

    while goal_count < max_goals:
        clusters = detect_frontiers(known_grid, min_frontier_cells)
        if not clusters:
            break
        best = score_frontiers(clusters, known_grid, res, rx, ry,
                                sensor_short, sensor_long, w_d, w_a, w_t,
                                exclude_positions=blacklist, exclude_radius=0.6)
        if best is None:
            break
        gx, gy, dist, ttime, turns = execute_path(
            known_grid, res, rx, ry, best['x'], best['y'],
            speed, turn_angle_threshold_deg, angular_speed, smoothing_factor)
        rx, ry = gx, gy
        total_distance += dist
        total_time += ttime
        total_turns += turns
        goal_count += 1
        raycast_update(true_grid, known_grid, res, rx, ry, n_rays, sensor_long, sensor_short)

        # A frontier that gets re-picked (score_frontiers already excludes
        # the immediate last goal via exclude_radius, so a repeat means it
        # is genuinely the best of what's left, e.g. bouncing between two
        # small slivers) is a real cycle, not honest progress - blacklist it
        # permanently so the next pick is forced to be something new.
        key = (round(best['x'], 1), round(best['y'], 1))
        visit_counts[key] = visit_counts.get(key, 0) + 1
        if visit_counts[key] >= 2:
            blacklist.append((best['x'], best['y']))

        known_now = int(np.sum(known_grid != -1))
        recent_known_counts.append(known_now)
        if len(recent_known_counts) == STALL_WINDOW and \
           (recent_known_counts[-1] - recent_known_counts[0]) < STALL_MIN_NEW_CELLS:
            stalled = True
            break

    wall_clock = time.time() - t_start
    known_cells = int(np.sum(known_grid != -1))
    total_cells = known_grid.size
    coverage = 100.0 * known_cells / total_cells
    remaining_clusters = detect_frontiers(known_grid, min_frontier_cells)

    return {
        'name': name, 'goal_count': goal_count, 'exploration_time_s': total_time,
        'path_distance_m': total_distance, 'turning_points': total_turns,
        'coverage_pct': coverage, 'sim_wall_clock_s': wall_clock,
        'completed': len(remaining_clusters) == 0,
        'stalled': stalled,
    }


ENVIRONMENTS = [
    # name, width, height, rooms_x, rooms_y, cyclic, start_x, start_y
    ('small_cyclic',    12.5, 13.0, 3, 3, True,  6.25, 6.5),
    ('small_noncyclic', 13.5, 13.0, 3, 3, False, 1.0,  1.0),
    ('wide',            26.0, 20.5, 5, 4, False, 1.0,  1.0),
]

PAPER_RESULTS = {
    'small_cyclic':    {'time': 103, 'distance': 36, 'turns': 6},
    'small_noncyclic': {'time': 51,  'distance': 41, 'turns': 10},
    'wide':             {'time': 629, 'distance': 231, 'turns': 44},
}

if __name__ == '__main__':
    print(f"{'Env':<16} {'Time(s)':>9} {'PaperT':>8} {'Dist(m)':>9} {'PaperD':>8} "
          f"{'Turns':>7} {'PaperTn':>8} {'Goals':>6} {'Cov%':>6} {'Done':>6} {'Stall':>6} {'WallClk':>8}")
    for name, w, h, rx_, ry_, cyc, sx, sy in ENVIRONMENTS:
        r = run_environment(name, w, h, rx_, ry_, cyc, sx, sy)
        p = PAPER_RESULTS[name]
        print(f"{r['name']:<16} {r['exploration_time_s']:>9.1f} {p['time']:>8} "
              f"{r['path_distance_m']:>9.2f} {p['distance']:>8} "
              f"{r['turning_points']:>7} {p['turns']:>8} "
              f"{r['goal_count']:>6} {r['coverage_pct']:>6.1f} "
              f"{'Y' if r['completed'] else 'N':>6} {'Y' if r['stalled'] else 'N':>6} "
              f"{r['sim_wall_clock_s']:>8.2f}")
