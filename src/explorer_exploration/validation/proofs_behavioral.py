"""
Behavioural and statistical validation of the TAD implementation.

  V5  Ablation study        - does each of d/a/t materially change behaviour?
  V6  Discriminative power  - does TAD actually differ from the baseline?
  V7  Statistical validation- multi-seed, effect size, significance
  V9  Realistic-map cost    - runtime on a SLAM-like map, not random noise

Writes results_behavioral.json.
"""

import json
import os
import sys
import time

import numpy as np
from scipy import stats as sps

import harness

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'kinematic_sim'))
import tad_kinematic_sim as sim  # noqa: E402

RESULTS = {}
SEEDS = list(range(1, 21))

# Weight configurations. The final entry probes the POLARITY of the distance
# term: the implementation maximises F_n, so +w_d rewards FAR frontiers while
# -w_d rewards NEAR ones (classic travel-cost minimisation).
CONFIGS = {
    'TAD_full   (1,1,1)':   dict(w_d=1.0,  w_a=1.0, w_t=1.0),
    'd_only     (1,0,0)':   dict(w_d=1.0,  w_a=0.0, w_t=0.0),
    'a_only     (0,1,0)':   dict(w_d=0.0,  w_a=1.0, w_t=0.0),
    't_only     (0,0,1)':   dict(w_d=0.0,  w_a=0.0, w_t=1.0),
    'a+t        (0,1,1)':   dict(w_d=0.0,  w_a=1.0, w_t=1.0),
    'TAD_neg_d (-1,1,1)':   dict(w_d=-1.0, w_a=1.0, w_t=1.0),
}

# NON-cyclic on purpose: with cyclic=True the generator opens every doorway,
# so the map is identical for every seed (verified: 1 distinct map across 12
# seeds) and "replicates" would be the same trial repeated. Non-cyclic draws a
# random spanning tree per seed -> 12 distinct topologies. The start pose is
# also randomised per seed, so each seed is a genuinely independent trial.
ENV = dict(name='ablation_noncyclic', width_m=12.5, height_m=13.0,
           rooms_x=3, rooms_y=3, cyclic=False)


def start_pose_for(seed):
    """A free, wall-clear start cell for this seed's map."""
    rng = np.random.RandomState(seed)
    grid, res = sim.build_room_grid_map(
        ENV['width_m'], ENV['height_m'], 0.05,
        ENV['rooms_x'], ENV['rooms_y'], ENV['cyclic'], rng)
    from scipy import ndimage
    # Keep clear of walls so the robot does not start inside one.
    clear = ndimage.binary_erosion(grid == 0, np.ones((9, 9), dtype=bool))
    rows, cols = np.where(clear)
    pick = np.random.RandomState(seed + 9000).randint(len(rows))
    return float(cols[pick] * res), float(rows[pick] * res)


# ===========================================================================
# V5 / V7 - Ablation across seeds, with statistics
# ===========================================================================

def run_config(cfg, seed):
    sx, sy = start_pose_for(seed)
    r = sim.run_environment(
        ENV['name'], ENV['width_m'], ENV['height_m'],
        ENV['rooms_x'], ENV['rooms_y'], ENV['cyclic'],
        sx, sy, seed=seed, **cfg)
    r['start'] = (sx, sy)
    return r


def ci95(xs):
    xs = np.asarray(xs, dtype=float)
    n = len(xs)
    if n < 2:
        return (float('nan'), float('nan'))
    se = xs.std(ddof=1) / np.sqrt(n)
    h = se * sps.t.ppf(0.975, n - 1)
    return (float(xs.mean() - h), float(xs.mean() + h))


def cliffs_delta(a, b):
    """Non-parametric effect size: P(a>b) - P(a<b), in [-1, 1]."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    gt = sum(int(x > y) for x in a for y in b)
    lt = sum(int(x < y) for x in a for y in b)
    return (gt - lt) / (len(a) * len(b))


def v5_v7_ablation():
    print('\n=== V5/V7  Ablation + statistics ===')
    per_config = {}
    for label, cfg in CONFIGS.items():
        rows = []
        for seed in SEEDS:
            rows.append(run_config(cfg, seed))
        per_config[label] = {
            'coverage_pct':   [r['coverage_pct'] for r in rows],
            'path_distance_m': [r['path_distance_m'] for r in rows],
            'exploration_time_s': [r['exploration_time_s'] for r in rows],
            'goal_count':     [r['goal_count'] for r in rows],
            'turning_points': [r['turning_points'] for r in rows],
        }
        cov = per_config[label]['coverage_pct']
        dist = per_config[label]['path_distance_m']
        print(f"  {label}: coverage {np.mean(cov):6.2f}% +/- {np.std(cov, ddof=1):5.2f}  "
              f"distance {np.mean(dist):7.2f} m +/- {np.std(dist, ddof=1):6.2f}")

    stats_block = {}
    for label, d in per_config.items():
        stats_block[label] = {}
        for metric, xs in d.items():
            stats_block[label][metric] = {
                'mean': float(np.mean(xs)),
                'std': float(np.std(xs, ddof=1)),
                'median': float(np.median(xs)),
                'ci95': ci95(xs),
                'n': len(xs),
                'raw': [float(v) for v in xs],
            }

    # Paired comparisons against the full TAD configuration.
    base_label = 'TAD_full   (1,1,1)'
    comparisons = {}
    for label in CONFIGS:
        if label == base_label:
            continue
        comparisons[label] = {}
        for metric in ('coverage_pct', 'path_distance_m'):
            a = per_config[base_label][metric]
            b = per_config[label][metric]
            diffs = np.asarray(a, float) - np.asarray(b, float)
            if np.allclose(diffs, 0):
                p = 1.0
                stat = 0.0
            else:
                stat, p = sps.wilcoxon(a, b)
            comparisons[label][metric] = {
                'wilcoxon_stat': float(stat),
                'p_value': float(p),
                'cliffs_delta': float(cliffs_delta(a, b)),
                'mean_diff_full_minus_this': float(np.mean(a) - np.mean(b)),
                'significant_at_0.05': bool(p < 0.05),
            }
            print(f"    {base_label} vs {label} [{metric}]: "
                  f"dmean={np.mean(a)-np.mean(b):+8.2f}  p={p:.4f}  "
                  f"delta={cliffs_delta(a, b):+.2f}")

    RESULTS['V5_V7'] = {
        'seeds': SEEDS, 'environment': ENV,
        'configs': {k: v for k, v in CONFIGS.items()},
        'stats': stats_block, 'comparisons': comparisons,
        'baseline_label': base_label,
    }


# ===========================================================================
# V6 - Discriminative power: TAD vs nearest-frontier on identical inputs
# ===========================================================================

def v6_discriminative_power():
    """If TAD always chose what nearest-frontier chooses, the a/t terms would
    be inert. Measure how often the two disagree on identical map+pose."""
    print('\n=== V6  Discriminative power ===')
    rng = np.random.RandomState(2024)
    n_eval = 0
    n_diff = 0
    n_multi = 0
    dist_ratio = []

    for _ in range(400):
        g = rng.choice([0, -1, 100], size=(40, 40), p=[0.55, 0.35, 0.10]).astype(np.int16)
        robot = (float(rng.uniform(5, 35)), float(rng.uniform(5, 35)))
        c_t, s_t, b_t = harness.score(g, robot, min_frontier_size=4,
                                      short_range=2.0, long_range=9.0,
                                      scoring_mode='tad')
        c_n, s_n, b_n = harness.score(g, robot, min_frontier_size=4,
                                      short_range=2.0, long_range=9.0,
                                      scoring_mode='nearest')
        if c_t is None or c_n is None or len(c_t) < 2:
            continue
        n_eval += 1
        n_multi += len(c_t)
        same = (abs(c_t[b_t]['x'] - c_n[b_n]['x']) < 1e-9
                and abs(c_t[b_t]['y'] - c_n[b_n]['y']) < 1e-9)
        if not same:
            n_diff += 1
        # How much farther is TAD willing to travel than the nearest option?
        d_near = min(x['d'] for x in c_t)
        if d_near > 1e-6:
            dist_ratio.append(c_t[b_t]['d'] / d_near)

    rate = n_diff / n_eval if n_eval else 0.0
    RESULTS['V6'] = {
        'decision_points': n_eval,
        'divergent_decisions': n_diff,
        'divergence_rate': rate,
        'mean_candidates_per_decision': n_multi / n_eval if n_eval else 0.0,
        'tad_to_nearest_distance_ratio_mean': float(np.mean(dist_ratio)) if dist_ratio else float('nan'),
        'tad_to_nearest_distance_ratio_median': float(np.median(dist_ratio)) if dist_ratio else float('nan'),
        'passed': bool(0.05 < rate < 1.0),
    }
    print(f"  decision points: {n_eval}, divergent: {n_diff} ({rate*100:.1f}%)")
    print(f"  mean candidates/decision: {n_multi/max(n_eval,1):.1f}")
    print(f"  TAD chosen-distance / nearest-distance: "
          f"mean {np.mean(dist_ratio):.2f}x, median {np.median(dist_ratio):.2f}x")


# ===========================================================================
# V9 - Cost on a realistic (structured) map rather than random noise
# ===========================================================================

def v9_realistic_cost():
    """Random grids create pathologically many tiny clusters. Re-measure on
    a structured room map, which is what the node actually sees from SLAM."""
    print('\n=== V9  Realistic-map runtime ===')
    from scipy import ndimage
    rng = np.random.RandomState(42)
    true_grid, res = sim.build_room_grid_map(12.5, 13.0, 0.05, 3, 3, True, rng)
    known = np.full_like(true_grid, -1)
    sim.raycast_update(true_grid, known, res, 6.25, 6.5, 720, 5.0, 0.5)

    free = (known == 0)
    unk = (known == -1)
    fm = np.zeros_like(free, dtype=bool)
    fm[:-1, :] |= free[:-1, :] & unk[1:, :]
    fm[1:, :] |= free[1:, :] & unk[:-1, :]
    fm[:, :-1] |= free[:, :-1] & unk[:, 1:]
    fm[:, 1:] |= free[:, 1:] & unk[:, :-1]
    _, K = ndimage.label(fm)

    node = harness.get_node()
    node.min_frontier_size = 7
    node.short_range, node.long_range = 0.5, 3.5
    node.w_d = node.w_a = node.w_t = 1.0
    node.scoring_mode = 'tad'
    node.get_robot_pose = lambda: (6.25, 6.5)
    node.publish_markers = lambda *a: None
    node.publish_goal = lambda *a: None
    node.clear_markers = lambda: None
    node.complete_pub.publish = lambda m: None
    msg = harness.make_grid(known, res, (0.0, 0.0))

    node.process_map(msg)
    reps = 10
    t0 = time.perf_counter()
    for _ in range(reps):
        node.process_map(msg)
    dt = (time.perf_counter() - t0) / reps

    RESULTS['V9'] = {
        'grid_cells': int(known.size),
        'grid_shape': list(known.shape),
        'frontier_clusters': int(K),
        'seconds_per_update': float(dt),
        'hz': float(1.0 / dt) if dt > 0 else float('inf'),
    }
    print(f"  structured map {known.shape} = {known.size} cells, {K} clusters")
    print(f"  process_map: {dt*1000:.2f} ms/update  ({1.0/dt:.1f} Hz)")


def main():
    v5_v7_ablation()
    v6_discriminative_power()
    v9_realistic_cost()

    out = os.path.join(os.path.dirname(__file__), 'results_behavioral.json')
    with open(out, 'w') as f:
        json.dump(RESULTS, f, indent=2, default=lambda o: (
            bool(o) if isinstance(o, np.bool_) else
            int(o) if isinstance(o, np.integer) else
            float(o) if isinstance(o, np.floating) else str(o)))
    print(f'\nWrote {out}')
    harness.shutdown()


if __name__ == '__main__':
    main()
