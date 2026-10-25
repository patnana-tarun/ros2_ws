---
tags: [issue]
---
# Planner comparison 2026-10-18

A/B test of the global planner: **NavFn** (current) against **Smac Lattice**. This is candidate
fix 1 from [[Path tracking and stalls 2026-10-18]], whose diagnosis motivates it: NavFn plans
for a round robot, gives every pose heading 0 and produces jagged paths, so MPPI stalls where
the rectangular footprint can't follow, and the robot replans every 0.53 s.

## Method
| | |
|---|---|
| A (control) | `config/nav2_params.yaml`: `nav2_navfn_planner::NavfnPlanner`, tolerance 0.3, `allow_unknown` |
| B (candidate) | `config/nav2_params_smac.yaml` (branch `exp/planner-tuning`): identical except the `GridBased` block: `nav2_smac_planner::SmacPlannerLattice` with Jazzy's `5cm_resolution/0.5m_turning_radius/diff` primitives (16 headings; straights, 0.5 m arcs, in-place pivots), tolerance 0.3, `allow_unknown`, Nav2's default Lattice weights |
| Runs | 3 pairs × 10 min of sim time each, from the first plan. Cave world, spawn (0, 0), TAD + DFS exploration, `bringup.launch.py gui:=false rviz:=false` |
| Fairness | A and B ran **side by side** in each pair, so both had the same machine load. Each had its own `ROS_DOMAIN_ID` and `GZ_PARTITION`, with local-only discovery. Rendering was on the RTX 4060 |
| Measured | A recorder node per run (`/map`, `/plan`, `/odom`, `/cmd_vel_nav`, TF, `global_costmap`, `is_path_valid`) plus counts from the launch log within the same 600 s window |
| Reproduce | `PAIRS=3 DUR=600 bash run_ab.sh`, then `python3 analyze.py`, then `figures.py`. All are in `assets/navigation/planner-comparison/`, with `summary.json` holding every per-run number |

## Results
Mean ± sd over 3 runs. "Pairs" counts the pairs where Smac was better. p is Welch's t-test; with
n = 3, only large and consistent effects reach p < 0.05.

**What Smac was chosen to fix: the path itself**

| Metric | NavFn | Smac | Change | Pairs | p |
|---|---|---|---|---|---|
| Path turning (°/m) | 97.6 ± 22.8 | 47.4 ± 14.9 | −51 % | 3/3 | 0.04 |
| Kinks > 30° per m | 0.74 ± 0.31 | 0.05 ± 0.09 | −93 % | 3/3 | 0.05 |
| Path poses with a real heading | 0 % | 92 % | — | 3/3 | — |
| Replans per minute | 31.2 ± 4.5 | 19.3 ± 4.0 | −38 % | 3/3 | 0.03 |
| Replaced plan invalid (`is_path_valid`) | 67 ± 6 % | 49 ± 12 % | −26 % | 3/3 | 0.12 |
| Path footprint touching inscribed cost | 21.9 ± 11.8 % | 24.4 ± 8.5 % | +12 % | 1/3 | 0.78 |

**Effect on the robot**

| Metric | NavFn | Smac | Change | Pairs | p |
|---|---|---|---|---|---|
| "Failed to make progress" | 14.0 ± 7.2 | 9.3 ± 2.1 | −33 % | 3/3 | 0.38 |
| Stall time, MPPI ≈ 0 for > 3 s | 164 ± 82 s | 109 ± 34 s | −33 % | 2/3 | 0.38 |
| Goals reached / sent | 6.0 / 11.7 | 7.0 / 12.7 | +17 % | 2/3 | 0.59 |
| Goals timed out by the coordinator | 4.7 ± 2.3 | 3.7 ± 0.6 | −21 % | 2/3 | 0.54 |
| Explored area at 5 min | 25.3 ± 3.2 m² | 34.0 ± 9.3 m² | +34 % | 3/3 | 0.24 |
| Explored area at 10 min | 58.4 ± 7.6 m² | 58.3 ± 15.8 m² | 0 % | 1/3 | 0.99 |
| Distance driven | 33.9 ± 10.1 m | 38.7 ± 8.2 m | +14 % | 2/3 | 0.55 |
| Controller missed-rate warnings | 5.0 ± 2.0 | 4.0 ± 1.0 | −20 % | 1/3 | 0.50 |
| Time > 10 cm off the path | 5.0 ± 0.5 % | 8.2 ± 1.3 % | +64 % | 0/3 | 0.04 |
| Cross-track error p50 / p90 / p99 | 2.1 / 7.4 / 18.3 cm | 1.5 / 8.9 / 19.0 cm | — | — | — |

**Costs**

| Metric | NavFn | Smac | Change | Pairs |
|---|---|---|---|---|
| Planning failures ("no valid path") | 4.0 ± 4.6 | 29.7 ± 16.2 | ×7 | 0/3 |
| … over distinct goals | 0.7 | 3.0 | — | 0/3 |
| Spin recoveries | 0.7 | 4.0 | ×6 | 0/3 |
| BackUp recoveries | 5.3 | 7.0 | +31 % | 0/3 |
| Plans slower than 50 ms (per run) | 1.7 | 37.3 (median 145 ms, max 814 ms) | — | 0/3 |
| `planner_server` CPU, including its global costmap | 103 ± 1 s | 166 ± 31 s | +62 % | 0/3 |

![[planner_ab_area.png]]
*Explored free area over 10 min. Smac is ahead from about minute 3 to minute 9. At 10 min the
means are equal, because one Smac run (run 2) stayed on 35–40 m² for its last 4 min.*

![[planner_ab_metrics.png]]
*Per-run values. The path-shape panels (top row) separate cleanly. The outcome panels overlap.*

## Explanation
- **The path got better, as intended, and consistently.** Smac only joins drivable motions and
  collision-checks the real 0.32 × 0.22 m footprint at each of 16 headings. Its paths turn half
  as much per metre, have almost no sharp kinks, and carry real headings. So `is_path_valid`
  rejects fewer of them and the robot replans 38 % less. All of these held in 3 of 3 pairs.
- **Stalls dropped, but not conclusively.** Progress failures fell in 3 of 3 pairs, and stall
  time by a third on average. The spread is large, though: NavFn's run 2 alone had 22 progress
  failures. With n = 3 this is a trend, not proof.
- **Paths still hug rocks.** The planner sees the same thin 0.22 m / 12 inflation band as before,
  and Smac's `cost_penalty` can only act inside that band. That part of the root cause is
  untouched by changing the planner.
- **Smac refuses goals NavFn accepted.** Its footprint check rejects frontier goals that only a
  round robot could reach: 2–4 goals per run, each retried many times. NavFn hands such a goal
  to MPPI, which then stalls on the way. Smac fails earlier, at the planner, but the BT's response
  (clear the global costmap, then BackUp / Spin / Wait in turn) costs about the time saved. That
  is why there are more spins and backups, and why area at 10 min comes out equal.
- **More time > 10 cm off the path (5.0 → 8.2 %).** The likely cause is MPPI cutting the 0.5 m
  arcs and in-place pivots that Smac paths contain, since `PathAlignCritic` rarely engages
  ([[Path tracking and stalls 2026-10-18]] §3). The median error is lower; the tail is what
  grew. Not verified.
- **Compute.** Most Smac plans are fast, but 37 per run took over 50 ms (up to 0.8 s). That
  exceeds the planner's expected 20 Hz rate but is well inside the BT's 2 Hz replanning tick.

## Verdict
Smac Lattice is the right planner **for the path-quality problem it was chosen for**. The
evidence for that is consistent and, for turning, kinks and replanning, significant at
p ≤ 0.05 despite n = 3. On its own it does **not** yet explore faster: about 30 % fewer stalls
are offset by refused goals and the recoveries they trigger. Before adopting it, two follow-ups
are indicated, then the same benchmark should be re-run:
1. When planning fails, the coordinator should drop that frontier at once and pick another,
   instead of leaving the BT to recover.
2. A longer inflation slope or a higher `cost_penalty`, to keep paths off rocks.
   [[Navigation stack]] records the gap-closure trade-off.

`nav2_params.yaml` on `feat/demo` still uses NavFn. The candidate and the follow-ups are on the
branch `exp/planner-tuning`, so `feat/demo` stays clean.

**Follow-up:** both follow-ups, and a re-run under different load, are in
[[Planner follow-ups 2026-10-18]]. Smac was not adopted.

## Limitations
- 3 runs per planner, 10 min each, in simulation only. Exploration order diverges between runs,
  so outcome metrics are noisy.
- Cross-track error is against the SLAM pose. Path clearance uses the global costmap when each
  plan arrives, sampled every 0.1 m at 25 footprint points with the tangent heading.
- `planner_server` CPU includes its global-costmap thread, so the CPU per plan isn't the pure
  planning time. Planning times come from Nav2's own "Planner loop missed" warnings, which only
  report plans over 50 ms.

All figures of this note, each with a one-line meaning: [[Planner comparison figures]].
