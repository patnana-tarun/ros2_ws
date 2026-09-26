"""
Controlled comparison of frontier-selection policies.

Experimental design
-------------------
Every arm of the experiment shares the same map generator, sensor model,
motion model, frontier detector, candidate features, anti-cycling guard and
termination rules. The ONLY difference between arms is the function that
chooses which frontier to visit. Policies are evaluated on identical
(map, start-pose) pairs, so the design is fully paired/blocked.

Primary metric
--------------
Area under the coverage-versus-distance curve, normalised by a common
distance budget. Following Holz et al. (2010), exploration efficiency is
about covering ground SOONER, not merely covering it eventually; a
final-coverage metric would reward a policy that terminates early and
penalise one that keeps working. AUC integrates the whole trajectory.

Hyperparameter protocol
-----------------------
Tunable policies (CU-exp, CU-lin, TAD-tuned) are tuned on TUNE_SEEDS and
evaluated on EVAL_SEEDS, which are disjoint. Competitors are tuned by the
same procedure and budget as our own method, so the comparison is not
rigged in our favour.
"""

import json
import math
import os
import sys
import time
from collections import deque

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'kinematic_sim'))
import tad_kinematic_sim as sim  # noqa: E402

from policies import POLICIES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# Disjoint seed sets: tuning never sees an evaluation map.
TUNE_SEEDS = list(range(101, 113))
EVAL_SEEDS = list(range(1, 21))

ENVIRONMENTS = {
    # label: (width_m, height_m, rooms_x, rooms_y, cyclic, distance budget m)
    'rooms_3x3':  (12.5, 13.0, 3, 3, False, 70.0),
    'rooms_4x4':  (17.0, 17.0, 4, 4, False, 110.0),
    'open_2x2':   (12.5, 13.0, 2, 2, False, 55.0),
}

RESOLUTION = 0.05
SENSOR_SHORT = 0.5
SENSOR_LONG = 5.0
N_RAYS = 720
MIN_FRONTIER_M = 0.35
SPEED = 0.2
ANG_SPEED = 1.0
TURN_THRESH_DEG = 45.0
SMOOTHING = 0.5
MAX_GOALS = 400
STALL_WINDOW = 5
STALL_MIN_NEW_CELLS = 15
EXCLUDE_RADIUS = 0.6

CONNECTIVITY_8 = np.ones((3, 3), dtype=bool)


# ---------------------------------------------------------------------------
# Shared candidate feature extraction - identical for every policy.
# ---------------------------------------------------------------------------

def extract_candidates(known, res, rx, ry, min_cells):
    """Frontier clusters plus the d / a / t / cells features.

    This mirrors frontier_tad_node.py exactly. The validation dossier
    established (V4) that the node and this formulation agree on 200/200
    randomised trials with zero deviation, so the TAD arm below is the
    production algorithm and not an approximation of it.
    """
    h, w = known.shape
    free = (known == 0)
    unknown = (known == -1)

    fm = np.zeros_like(free, dtype=bool)
    fm[:-1, :] |= free[:-1, :] & unknown[1:, :]
    fm[1:, :] |= free[1:, :] & unknown[:-1, :]
    fm[:, :-1] |= free[:, :-1] & unknown[:, 1:]
    fm[:, 1:] |= free[:, 1:] & unknown[:, :-1]
    if not np.any(fm):
        return []

    # 8-connectivity for frontier CLUSTERING. A frontier is a curve through
    # the grid and generally runs diagonally; under 4-connectivity a diagonal
    # run is a staircase whose cells touch only at corners, so one real
    # frontier shatters into many tiny fragments which the minimum-size
    # filter then discards. Measured on a representative map: 4-connectivity
    # yields 76 clusters (largest 8 cells), 8-connectivity yields 24 (largest
    # 75). Detection of frontier CELLS remains 4-neighbour, which is standard.
    labeled, num = ndimage.label(fm, structure=CONNECTIVITY_8)
    unknown_labeled, _ = ndimage.label(unknown)
    unknown_sizes = np.bincount(unknown_labeled.ravel())

    rcol, rrow = rx / res, ry / res
    out = []
    for cid in range(1, num + 1):
        ys, xs = np.where(labeled == cid)
        n = len(xs)
        if n < min_cells:
            continue
        cy, cx = float(np.mean(ys)), float(np.mean(xs))
        wx, wy = cx * res, cy * res
        d = float(np.hypot(wx - rx, wy - ry))

        roff = ys + np.array([-1, 1, 0, 0])[:, None]
        coff = xs + np.array([0, 0, -1, 1])[:, None]
        touched = set()
        for r_o, c_o in zip(roff, coff):
            ok = (r_o >= 0) & (r_o < h) & (c_o >= 0) & (c_o < w)
            for r, c in zip(r_o[ok], c_o[ok]):
                lbl = unknown_labeled[r, c]
                if lbl:
                    touched.add(lbl)
        a = float(sum(unknown_sizes[l] for l in touched)) * res ** 2

        cd = np.hypot(xs - rcol, ys - rrow) * res
        inner = int(np.sum(cd <= SENSOR_SHORT))
        outer = int(np.sum((cd > SENSOR_SHORT) & (cd <= SENSOR_LONG)))
        t = 1.0 if outer > inner else (0.0 if outer == inner else -1.0)

        out.append({'x': wx, 'y': wy, 'd': d, 'a': a, 't': t, 'cells': n})
    return out


# ---------------------------------------------------------------------------
# Start pose (identical for a given seed, across all policies)
# ---------------------------------------------------------------------------

def start_pose(env, seed):
    w, h, rx, ry, cyc, _ = ENVIRONMENTS[env]
    grid, res = sim.build_room_grid_map(w, h, RESOLUTION, rx, ry, cyc,
                                        np.random.RandomState(seed))
    clear = ndimage.binary_erosion(grid == 0, np.ones((9, 9), dtype=bool))
    rows, cols = np.where(clear)
    pick = np.random.RandomState(seed + 9000).randint(len(rows))
    return grid, res, float(cols[pick] * res), float(rows[pick] * res)


# ---------------------------------------------------------------------------
# One exploration episode
# ---------------------------------------------------------------------------

def run_episode(env, seed, policy_name, params):
    spec = POLICIES[policy_name]
    select = spec['fn']
    budget = ENVIRONMENTS[env][5]
    hard_cap = budget * 2.0

    true_grid, res, rx, ry = start_pose(env, seed)
    known = np.full_like(true_grid, -1)
    min_cells = max(1, int(round(MIN_FRONTIER_M / res)))
    rng = np.random.RandomState(seed * 7919 + 13)

    sim.raycast_update(true_grid, known, res, rx, ry, N_RAYS, SENSOR_LONG, SENSOR_SHORT)

    total_cells = known.size
    cov = lambda: 100.0 * float(np.sum(known != -1)) / total_cells

    dist_total = 0.0
    time_total = 0.0
    turns_total = 0
    goals = 0
    decision_ms = []
    trace = [(0.0, cov())]

    blacklist = []
    visit_counts = {}
    recent_known = deque(maxlen=STALL_WINDOW)
    recent_known.append(int(np.sum(known != -1)))
    stalled = False

    while goals < MAX_GOALS and dist_total < hard_cap:
        cands = extract_candidates(known, res, rx, ry, min_cells)
        if not cands:
            break

        usable = cands
        if blacklist:
            filt = [c for c in cands
                    if all(math.hypot(c['x'] - bx, c['y'] - by) > EXCLUDE_RADIUS
                           for bx, by in blacklist)]
            if not filt:
                break
            usable = filt

        t0 = time.perf_counter()
        idx = select(usable, rng, **params)
        decision_ms.append((time.perf_counter() - t0) * 1000.0)
        best = usable[idx]

        gx, gy, dist, ttime, turns = sim.execute_path(
            known, res, rx, ry, best['x'], best['y'],
            SPEED, TURN_THRESH_DEG, ANG_SPEED, SMOOTHING)
        rx, ry = gx, gy
        dist_total += dist
        time_total += ttime
        turns_total += turns
        goals += 1
        sim.raycast_update(true_grid, known, res, rx, ry, N_RAYS, SENSOR_LONG, SENSOR_SHORT)
        trace.append((dist_total, cov()))

        key = (round(best['x'], 1), round(best['y'], 1))
        visit_counts[key] = visit_counts.get(key, 0) + 1
        if visit_counts[key] >= 2:
            blacklist.append((best['x'], best['y']))

        known_now = int(np.sum(known != -1))
        recent_known.append(known_now)
        if len(recent_known) == STALL_WINDOW and \
           (recent_known[-1] - recent_known[0]) < STALL_MIN_NEW_CELLS:
            stalled = True
            break

    return {
        'env': env, 'seed': seed, 'policy': policy_name,
        'final_coverage': cov(),
        'distance_m': dist_total,
        'time_s': time_total,
        'turns': turns_total,
        'goals': goals,
        'stalled': stalled,
        'decision_ms_mean': float(np.mean(decision_ms)) if decision_ms else 0.0,
        'auc': auc_coverage(trace, budget),
        'dist_to_50': dist_to_coverage(trace, 50.0),
        'dist_to_75': dist_to_coverage(trace, 75.0),
        'trace': trace,
    }


def auc_coverage(trace, budget):
    """Mean coverage over [0, budget] of the step-held coverage(distance)
    curve. Coverage is held flat past termination, so stopping early yields
    no advantage. Units are coverage-percent; higher is better."""
    area = 0.0
    for i in range(len(trace) - 1):
        d0, c0 = trace[i]
        d1, _ = trace[i + 1]
        if d0 >= budget:
            break
        seg = min(d1, budget) - d0
        area += c0 * seg          # coverage held at c0 until the next goal
    last_d, last_c = trace[-1]
    if last_d < budget:
        area += last_c * (budget - last_d)
    return area / budget


def dist_to_coverage(trace, target):
    for d, c in trace:
        if c >= target:
            return d
    return float('nan')          # censored: never reached


# ---------------------------------------------------------------------------
# Hyperparameter tuning on held-out seeds
# ---------------------------------------------------------------------------

LAM_GRID = [0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2, 2.0]
WEIGHT_GRID = [
    (1.0, 1.0, 1.0), (1.0, 2.0, 1.0), (1.0, 1.0, 2.0), (1.0, 2.0, 2.0),
    (0.5, 1.0, 1.0), (0.5, 2.0, 1.0), (0.25, 1.0, 1.0), (0.25, 2.0, 2.0),
    (2.0, 1.0, 1.0), (0.0, 1.0, 1.0), (1.0, 3.0, 1.0), (0.5, 1.0, 2.0),
]


def tune_hyperparameters(verbose=True):
    tuned = {}
    for name, spec in POLICIES.items():
        if spec['tunable'] is None:
            tuned[name] = dict(spec['params'])
            continue
        if spec['tunable'] == 'lam':
            grid = [dict(lam=l) for l in LAM_GRID]
        else:
            grid = [dict(w_d=a, w_a=b, w_t=c) for (a, b, c) in WEIGHT_GRID]

        best, best_score = None, -np.inf
        for params in grid:
            scores = []
            for env in ENVIRONMENTS:
                for seed in TUNE_SEEDS:
                    scores.append(run_episode(env, seed, name, params)['auc'])
            m = float(np.mean(scores))
            if m > best_score:
                best, best_score = params, m
        tuned[name] = best
        if verbose:
            print(f'  tuned {name:10s} -> {best}  (held-out AUC {best_score:.2f})')
    return tuned


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(tuned, verbose=True):
    rows = []
    for name in POLICIES:
        params = tuned[name]
        for env in ENVIRONMENTS:
            for seed in EVAL_SEEDS:
                r = run_episode(env, seed, name, params)
                r['params'] = params
                rows.append(r)
        if verbose:
            sub = [r for r in rows if r['policy'] == name]
            print(f"  {name:10s} AUC {np.mean([r['auc'] for r in sub]):6.2f}  "
                  f"cov {np.mean([r['final_coverage'] for r in sub]):5.1f}%  "
                  f"dist {np.mean([r['distance_m'] for r in sub]):6.1f} m")
    return rows


def main():
    t0 = time.time()
    print('Tuning hyperparameters on held-out seeds '
          f'{TUNE_SEEDS[0]}-{TUNE_SEEDS[-1]} ...')
    tuned = tune_hyperparameters()

    print(f'\nEvaluating on seeds {EVAL_SEEDS[0]}-{EVAL_SEEDS[-1]} '
          f'x {len(ENVIRONMENTS)} environments ...')
    rows = evaluate(tuned)

    out = os.path.join(HERE, 'results_comparison.json')
    payload = {
        'tuned': tuned,
        'tune_seeds': TUNE_SEEDS,
        'eval_seeds': EVAL_SEEDS,
        'environments': {k: list(v) for k, v in ENVIRONMENTS.items()},
        'runs': rows,
        'wall_clock_s': time.time() - t0,
    }
    with open(out, 'w') as f:
        json.dump(payload, f, default=lambda o: (
            bool(o) if isinstance(o, np.bool_) else
            int(o) if isinstance(o, np.integer) else
            float(o) if isinstance(o, np.floating) else str(o)))
    print(f'\nWrote {out}  ({time.time()-t0:.0f}s total)')


if __name__ == '__main__':
    main()
