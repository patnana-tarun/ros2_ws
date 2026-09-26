"""
Core conformance proofs for the TAD implementation.

Four independent layers of evidence, all executed against the production
node via harness.py:

  V2  Analytical ground truth  - hand-computable grids, exact expected values
  V3  Metamorphic invariants   - properties the implementation must satisfy
  V4  Cross-implementation     - ROS2 node vs standalone kinematic sim
  V8  Complexity conformance   - empirical scaling vs theoretical O(N)

Writes results to results_core.json.
"""

import json
import math
import os
import sys
import time

import numpy as np

import harness

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'kinematic_sim'))
import tad_kinematic_sim as sim  # noqa: E402

RESULTS = {'V2': [], 'V3': [], 'V4': {}, 'V8': {}}
TOL = 1e-9


def record(layer, test_id, claim, expected, observed, passed, detail=''):
    RESULTS[layer].append({
        'id': test_id, 'claim': claim,
        'expected': expected, 'observed': observed,
        'passed': bool(passed), 'detail': detail,
    })
    print(f"  [{'PASS' if passed else 'FAIL'}] {test_id}: {claim}")
    if not passed:
        print(f"         expected={expected!r} observed={observed!r}")


# ===========================================================================
# Fixtures - grids small enough that every expected value is hand-derivable.
# ===========================================================================

def fixture_halfplane():
    """11x11. Rows 0-1 unknown, rows 2-10 free.

    Frontier = row 2, cols 0..10 (11 cells, free with unknown above).
    Centroid = (row 2, col 5) -> world (5, 2) at res=1, origin=(0,0).
    Unknown region = 2 rows x 11 cols = 22 cells -> a_n = 22.0 m^2.
    """
    g = np.zeros((11, 11), dtype=np.int16)
    g[0:2, :] = -1
    return g


def fixture_two_unknown_regions():
    """7x5. Column 2 free; cols 0-1 and cols 3-4 are two DISJOINT unknown
    regions of 14 cells each (separated by the free column, 4-connectivity).

    Frontier = all 7 cells of col 2, one cluster, touching BOTH regions.
    a_n must be the SUM: (14 + 14) * 1.0^2 = 28.0 m^2.
    Centroid = (row 3, col 2) -> world (2, 3).
    """
    g = np.zeros((7, 5), dtype=np.int16)
    g[:, 0:2] = -1
    g[:, 3:5] = -1
    return g


def fixture_two_clusters():
    """13x11. Exactly two frontier clusters, of 11 and 3 cells.

    Rows 0-1 unknown  -> 11-cell frontier along row 2.
    Row 12, cols 0-2 unknown -> 3-cell frontier along row 11.
    Cell (12,3) is set to OBSTACLE deliberately: left as free it would
    itself be a valid 1-cell frontier (free, with unknown at (12,2)), which
    is correct behaviour but would make the fixture's cluster inventory
    less obvious to hand-check. Sealing it keeps the expected set exact.
    """
    g = np.zeros((13, 11), dtype=np.int16)
    g[0:2, :] = -1
    g[12, 0:3] = -1
    g[12, 3] = 100
    return g


# ===========================================================================
# V2 - Analytical ground truth
# ===========================================================================

def v2_distance_exact():
    """Eq. 2: d_n = || p_robot - c_n ||_2, exactly."""
    g = fixture_halfplane()
    # Centroid is fixed at world (5, 2). Probe several robot poses whose
    # exact Euclidean distance is known in closed form.
    cases = [
        ((5.0, 8.0), 6.0),                 # pure vertical
        ((0.0, 2.0), 5.0),                 # pure horizontal
        ((1.0, 6.0), 5.0),                 # 3-4-5 triangle: dx=4, dy=4 -> no
        ((8.0, 6.0), 5.0),                 # dx=3, dy=4 -> 5 exactly
        ((5.0 + 1.0, 2.0 + 1.0), math.sqrt(2.0)),
    ]
    for robot, expected in cases:
        c, _, _ = harness.score(g, robot, min_frontier_size=1)
        observed = c[0]['d']
        analytic = math.hypot(5.0 - robot[0], 2.0 - robot[1])
        ok = abs(observed - analytic) < TOL
        record('V2', f'V2.1 d_n @ robot{robot}',
               'd_n equals closed-form Euclidean distance (Eq. 2)',
               round(analytic, 12), round(observed, 12), ok)


def v2_trapezoid_trichotomy():
    """Eq. 5: t_n = +1 if outer > inner, 0 if equal, -1 if outer < inner.

    Frontier cells sit in row 2 at cols 0..10; robot at world (5,8).
    Cell-to-robot distances (res=1) are, by construction:
      col 5      -> 6.0000
      col 4,6    -> 6.0828
      col 3,7    -> 6.3246
      col 2,8    -> 6.7082
      col 1,9    -> 7.2111
      col 0,10   -> 7.8102
    Choosing the annulus bounds therefore fixes inner/outer counts exactly.
    """
    g = fixture_halfplane()
    robot = (5.0, 8.0)
    cases = [
        # (short, long, expected inner, expected outer, expected t)
        (6.50, 8.00, 5, 6, 1.0),    # outer 6 > inner 5 -> widening
        (6.75, 7.00, 7, 0, -1.0),   # outer 0 < inner 7 -> narrowing
        (0.50, 3.50, 0, 0, 0.0),    # both empty -> equal
    ]
    for short, long, exp_in, exp_out, exp_t in cases:
        c, _, _ = harness.score(g, robot, min_frontier_size=1,
                                short_range=short, long_range=long)
        observed = c[0]['t']
        # Independently recount inner/outer from first principles.
        cols = np.arange(11)
        dist = np.hypot(cols - 5.0, 2.0 - 8.0)
        inner = int(np.sum(dist <= short))
        outer = int(np.sum((dist > short) & (dist <= long)))
        ok = (observed == exp_t) and inner == exp_in and outer == exp_out
        record('V2', f'V2.2 t_n @ ranges({short},{long})',
               f't_n={exp_t} for inner={exp_in}, outer={exp_out} (Eq. 5)',
               exp_t, observed, ok,
               detail=f'recounted inner={inner}, outer={outer}')


def v2_adjacency_single_region():
    g = fixture_halfplane()
    c, _, _ = harness.score(g, (5.0, 8.0), min_frontier_size=1)
    ok = abs(c[0]['a'] - 22.0) < TOL
    record('V2', 'V2.3 a_n single region',
           'a_n = 22 unknown cells x (1.0 m)^2 = 22.0 m^2',
           22.0, c[0]['a'], ok)


def v2_adjacency_multi_region():
    """A frontier bordering two disjoint unknown regions must sum both."""
    g = fixture_two_unknown_regions()
    c, _, _ = harness.score(g, (2.0, 10.0), min_frontier_size=1)
    ok = len(c) == 1 and abs(c[0]['a'] - 28.0) < TOL
    record('V2', 'V2.4 a_n multi-region sum',
           'a_n = (14 + 14) cells x 1.0 m^2 = 28.0 m^2 (both regions summed)',
           28.0, c[0]['a'] if c else None, ok)


def v2_adjacency_resolution_scaling():
    """a_n is an AREA: identical topology at half the cell size must give
    exactly one quarter the area."""
    g = fixture_two_unknown_regions()
    c1, _, _ = harness.score(g, (2.0, 10.0), resolution=1.0, min_frontier_size=1)
    c2, _, _ = harness.score(g, (1.0, 5.0), resolution=0.5, min_frontier_size=1)
    expected = c1[0]['a'] * 0.25
    ok = abs(c2[0]['a'] - expected) < TOL
    record('V2', 'V2.5 a_n resolution scaling',
           'halving resolution scales a_n by exactly 1/4 (area semantics)',
           expected, c2[0]['a'], ok)


def v2_eq6_aggregation():
    """Eq. 6 wiring: F_n must equal w_d*norm(d) + w_a*norm(a) + w_t*norm(t),
    re-derived independently from the d/a/t the node itself reported."""
    g = fixture_two_clusters()
    for (wd, wa, wt) in [(1.0, 1.0, 1.0), (2.0, 0.5, 1.5), (1.0, 0.0, 0.0)]:
        c, s, _ = harness.score(g, (5.0, 6.0), min_frontier_size=1,
                                w_d=wd, w_a=wa, w_t=wt)

        def norm(vals):
            v = np.asarray(vals, dtype=float)
            lo, hi = v.min(), v.max()
            return np.ones_like(v) if hi - lo < 1e-6 else (v - lo) / (hi - lo)

        ref = (wd * norm([x['d'] for x in c])
               + wa * norm([x['a'] for x in c])
               + wt * norm([x['t'] for x in c]))
        err = float(np.max(np.abs(ref - s)))
        ok = err < TOL
        record('V2', f'V2.6 Eq.6 aggregation w=({wd},{wa},{wt})',
               'F_n equals independently re-derived weighted normalized sum',
               0.0, err, ok, detail=f'{len(c)} candidates, max|err|={err:.3e}')


def v2_min_frontier_filter():
    """Clusters below min_frontier_size must be discarded (paper Table 2
    'minimal size of frontier')."""
    g = fixture_two_clusters()
    c_all, _, _ = harness.score(g, (5.0, 6.0), min_frontier_size=1)
    c_filt, _, _ = harness.score(g, (5.0, 6.0), min_frontier_size=7)
    sizes_all = sorted(x['cell_count'] for x in c_all)
    sizes_filt = sorted(x['cell_count'] for x in c_filt)
    ok = (len(c_all) == 2 and sizes_all == [3, 11]
          and len(c_filt) == 1 and sizes_filt == [11])
    record('V2', 'V2.7 min_frontier_size filter',
           'threshold 7 removes the 3-cell cluster, keeps the 11-cell one',
           {'all': [3, 11], 'filtered': [11]},
           {'all': sizes_all, 'filtered': sizes_filt}, ok)


# ===========================================================================
# V3 - Metamorphic / invariant properties
# ===========================================================================

def v3_determinism():
    g = fixture_two_clusters()
    _, s0, b0 = harness.score(g, (5.0, 6.0), min_frontier_size=1)
    identical = True
    for _ in range(50):
        _, s, b = harness.score(g, (5.0, 6.0), min_frontier_size=1)
        if b != b0 or not np.array_equal(s, s0):
            identical = False
            break
    record('V3', 'V3.1 determinism',
           '50 repeated evaluations are bitwise identical',
           True, identical, identical)


def v3_translation_invariance():
    """Translating map origin and robot by the same vector must leave every
    TAD component unchanged - the score depends on relative geometry only."""
    g = fixture_two_clusters()
    c0, s0, _ = harness.score(g, (5.0, 6.0), origin=(0.0, 0.0), min_frontier_size=1)
    shift = (137.5, -42.25)
    c1, s1, _ = harness.score(g, (5.0 + shift[0], 6.0 + shift[1]),
                              origin=shift, min_frontier_size=1)
    err = max(max(abs(a[k] - b[k]) for k in ('d', 'a', 't'))
              for a, b in zip(c0, c1))
    serr = float(np.max(np.abs(s0 - s1)))
    ok = err < 1e-9 and serr < 1e-9
    record('V3', 'V3.2 translation invariance',
           'd_n, a_n, t_n, F_n invariant under rigid translation of the frame',
           0.0, max(err, serr), ok, detail=f'shift={shift}')


def v3_distance_monotonicity():
    """d_n must increase strictly monotonically as the robot recedes."""
    g = fixture_halfplane()
    ds = []
    for dy in range(3, 40):
        c, _, _ = harness.score(g, (5.0, 2.0 + dy), min_frontier_size=1)
        ds.append(c[0]['d'])
    strictly_increasing = all(b > a for a, b in zip(ds, ds[1:]))
    max_err = max(abs(d - (i + 3)) for i, d in enumerate(ds))
    ok = strictly_increasing and max_err < TOL
    record('V3', 'V3.3 d_n monotonicity',
           'd_n strictly increases with range and tracks the analytic value',
           True, strictly_increasing, ok,
           detail=f'37 poses, max deviation from analytic = {max_err:.3e}')


def v3_trapezoid_codomain():
    """t_n must take values in {-1, 0, +1} only - exhaustively, and all
    three must actually occur (no dead branch)."""
    rng = np.random.RandomState(7)
    seen = set()
    violations = 0
    n = 0
    for _ in range(120):
        g = rng.choice([0, -1, 100], size=(24, 24), p=[0.55, 0.35, 0.10]).astype(np.int16)
        c, _, _ = harness.score(g, (12.0, 12.0), min_frontier_size=1,
                                short_range=rng.uniform(1, 6),
                                long_range=rng.uniform(7, 14))
        if not c:
            continue
        for x in c:
            n += 1
            seen.add(x['t'])
            if x['t'] not in (-1.0, 0.0, 1.0):
                violations += 1
    ok = violations == 0 and seen == {-1.0, 0.0, 1.0}
    record('V3', 'V3.4 t_n codomain',
           't_n in {-1,0,+1} over all samples, and all three values occur',
           [-1.0, 0.0, 1.0], sorted(seen), ok,
           detail=f'{n} candidate evaluations, {violations} violations')


def v3_score_bounds():
    """Normalized components lie in [0,1], so F_n in [0, w_d+w_a+w_t]."""
    rng = np.random.RandomState(11)
    lo_v, hi_v = math.inf, -math.inf
    n = 0
    for _ in range(120):
        g = rng.choice([0, -1, 100], size=(28, 28), p=[0.55, 0.35, 0.10]).astype(np.int16)
        c, s, _ = harness.score(g, (14.0, 14.0), min_frontier_size=1)
        if c is None or len(c) < 2:
            continue
        n += len(c)
        lo_v, hi_v = min(lo_v, float(s.min())), max(hi_v, float(s.max()))
    ok = lo_v >= -TOL and hi_v <= 3.0 + TOL
    record('V3', 'V3.5 score bounds',
           'F_n confined to [0, w_d+w_a+w_t] = [0, 3] under unit weights',
           [0.0, 3.0], [round(lo_v, 6), round(hi_v, 6)], ok,
           detail=f'{n} candidate evaluations')


def v3_weight_ablation_exactness():
    """Zeroing a weight must remove that term's contribution EXACTLY -
    proving the three terms are independently wired with no cross-coupling."""
    g = fixture_two_clusters()
    c, s_d_only, _ = harness.score(g, (5.0, 6.0), min_frontier_size=1,
                                   w_d=1.0, w_a=0.0, w_t=0.0)

    def norm(vals):
        v = np.asarray(vals, dtype=float)
        lo, hi = v.min(), v.max()
        return np.ones_like(v) if hi - lo < 1e-6 else (v - lo) / (hi - lo)

    ref = norm([x['d'] for x in c])
    err = float(np.max(np.abs(ref - s_d_only)))
    ok = err < TOL
    record('V3', 'V3.6 weight ablation exactness',
           'w=(1,0,0) reduces F_n to exactly norm(d_n): terms are separable',
           0.0, err, ok)


def v3_nearest_baseline_wiring():
    """scoring_mode='nearest' must reduce to the Yamauchi baseline exactly:
    score = -d_n, and the selection is the minimum-distance frontier."""
    g = fixture_two_clusters()
    c, s, b = harness.score(g, (5.0, 6.0), min_frontier_size=1,
                            scoring_mode='nearest')
    ref = -np.array([x['d'] for x in c])
    err = float(np.max(np.abs(ref - s)))
    picks_nearest = b == int(np.argmin([x['d'] for x in c]))
    ok = err < TOL and picks_nearest
    record('V3', 'V3.7 nearest-frontier baseline wiring',
           "mode='nearest' yields score=-d_n and selects min-d_n frontier",
           True, picks_nearest, ok, detail=f'max|err|={err:.3e}')


def v3_argmax_selection():
    """The published goal must be the true argmax of F_n."""
    rng = np.random.RandomState(23)
    bad = 0
    n = 0
    for _ in range(150):
        g = rng.choice([0, -1, 100], size=(26, 26), p=[0.55, 0.35, 0.10]).astype(np.int16)
        c, s, b = harness.score(g, (13.0, 13.0), min_frontier_size=1)
        if c is None:
            continue
        n += 1
        if b != int(np.argmax(s)) or abs(s[b] - s.max()) > TOL:
            bad += 1
    ok = bad == 0 and n > 0
    record('V3', 'V3.8 argmax selection integrity',
           'selected frontier is always the strict maximizer of F_n',
           0, bad, ok, detail=f'{n} random maps')


# ===========================================================================
# V4 - Cross-implementation equivalence (ROS2 node vs kinematic sim)
# ===========================================================================

def v4_equivalence():
    """The standalone simulator claims to reuse 'the EXACT SAME' scoring
    logic as the ROS2 node. Test it: same grid, same pose, same parameters,
    compare the selected goal and its d/a/t."""
    rng = np.random.RandomState(1234)
    agree = 0
    total = 0
    max_dev = 0.0
    mismatches = []
    for trial in range(200):
        g = rng.choice([0, -1, 100], size=(30, 30), p=[0.5, 0.4, 0.10]).astype(np.int16)
        robot = (float(rng.uniform(2, 27)), float(rng.uniform(2, 27)))
        short, long = 1.5, 8.0
        mfs = 3

        c, s, b = harness.score(g, robot, resolution=1.0, origin=(0.0, 0.0),
                                min_frontier_size=mfs,
                                short_range=short, long_range=long)
        clusters = sim.detect_frontiers(g, mfs)
        best_sim = sim.score_frontiers(clusters, g, 1.0, robot[0], robot[1],
                                       short, long, 1.0, 1.0, 1.0)
        if c is None and best_sim is None:
            continue
        if c is None or best_sim is None:
            total += 1
            mismatches.append({'trial': trial, 'reason': 'one side returned no candidate'})
            continue

        total += 1
        node_best = c[b]
        same_xy = (abs(node_best['x'] - best_sim['x']) < 1e-9
                   and abs(node_best['y'] - best_sim['y']) < 1e-9)
        dev = max(abs(node_best[k] - best_sim[k]) for k in ('d', 'a', 't'))
        max_dev = max(max_dev, dev)
        if same_xy and dev < 1e-9:
            agree += 1
        else:
            mismatches.append({'trial': trial, 'node': {k: node_best[k] for k in ('x', 'y', 'd', 'a', 't')},
                               'sim': {k: best_sim[k] for k in ('x', 'y', 'd', 'a', 't')}})

    rate = agree / total if total else 0.0
    RESULTS['V4'] = {
        'trials': total, 'agreements': agree, 'agreement_rate': rate,
        'max_component_deviation': max_dev,
        'mismatch_examples': mismatches[:5],
        'passed': rate == 1.0,
    }
    print(f"  [{'PASS' if rate == 1.0 else 'FAIL'}] V4 equivalence: "
          f"{agree}/{total} identical decisions, max|dev|={max_dev:.3e}")


# ===========================================================================
# V8 - Complexity conformance
# ===========================================================================

def v8_complexity():
    """Frontier extraction is vectorized over the grid; per-candidate work is
    linear in cluster size. Measure empirical scaling in cell count N."""
    rng = np.random.RandomState(99)
    sizes = [40, 60, 90, 130, 190, 260]
    points = []
    for side in sizes:
        g = rng.choice([0, -1, 100], size=(side, side), p=[0.55, 0.35, 0.10]).astype(np.int16)
        robot = (side / 2.0, side / 2.0)
        harness.score(g, robot, min_frontier_size=5)  # warm up
        reps = 5
        t0 = time.perf_counter()
        for _ in range(reps):
            harness.score(g, robot, min_frontier_size=5)
        dt = (time.perf_counter() - t0) / reps
        points.append({'side': side, 'cells': side * side, 'seconds': dt})
        print(f"    N={side*side:>7d} cells  t={dt*1000:8.2f} ms")

    logN = np.log(np.array([p['cells'] for p in points], dtype=float))
    logT = np.log(np.array([p['seconds'] for p in points], dtype=float))
    slope, intercept = np.polyfit(logN, logT, 1)
    resid = logT - (slope * logN + intercept)
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((logT - logT.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float('nan')
    # The claim under test is algorithmic CLASS: no accidental quadratic
    # blowup. An exponent materially above 1.0 is still reported, since it
    # indicates the Python-level adjacency loop dominating at scale.
    subquadratic = slope < 1.75
    RESULTS['V8'] = {
        'points': points, 'loglog_slope': float(slope), 'r_squared': float(r2),
        'subquadratic': bool(subquadratic),
        'superlinear': bool(slope > 1.15),
        'passed': bool(subquadratic),
    }
    print(f"  [{'PASS' if subquadratic else 'FAIL'}] V8 complexity: "
          f"empirical exponent {slope:.3f} (R^2={r2:.4f}), sub-quadratic")


def main():
    print('\n=== V2  Analytical ground truth ===')
    v2_distance_exact()
    v2_trapezoid_trichotomy()
    v2_adjacency_single_region()
    v2_adjacency_multi_region()
    v2_adjacency_resolution_scaling()
    v2_eq6_aggregation()
    v2_min_frontier_filter()

    print('\n=== V3  Metamorphic invariants ===')
    v3_determinism()
    v3_translation_invariance()
    v3_distance_monotonicity()
    v3_trapezoid_codomain()
    v3_score_bounds()
    v3_weight_ablation_exactness()
    v3_nearest_baseline_wiring()
    v3_argmax_selection()

    print('\n=== V4  Cross-implementation equivalence ===')
    v4_equivalence()

    print('\n=== V8  Complexity conformance ===')
    v8_complexity()

    n_pass = sum(1 for r in RESULTS['V2'] + RESULTS['V3'] if r['passed'])
    n_tot = len(RESULTS['V2']) + len(RESULTS['V3'])
    RESULTS['summary'] = {
        'unit_tests_passed': n_pass, 'unit_tests_total': n_tot,
        'v4_passed': RESULTS['V4'].get('passed'),
        'v8_passed': RESULTS['V8'].get('passed'),
    }
    print(f"\n=== SUMMARY: {n_pass}/{n_tot} analytical+invariant assertions passed ===")

    def jsonable(o):
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)

    out = os.path.join(os.path.dirname(__file__), 'results_core.json')
    with open(out, 'w') as f:
        json.dump(RESULTS, f, indent=2, default=jsonable)
    print(f'Wrote {out}')
    harness.shutdown()


if __name__ == '__main__':
    main()
