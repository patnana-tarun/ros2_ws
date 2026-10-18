---
tags: [issue]
---
# Tunnel tracking 2026-10-18

Can NavFn be kept and the robot made to drive straighter through tunnels, with less heading
deviation from the path and fewer random turns? Branch `exp/tunnel-tracking`. This follows
[[Planner follow-ups 2026-10-18]] (NavFn stays) and [[Path tracking and stalls 2026-10-18]]
(NavFn's kinks, and `PathAlignCritic` almost never scoring).

## Setups
| Setup | BT | MPPI |
|---|---|---|
| **base** | `explore_nav_to_pose.xml` | `nav2_params.yaml` |
| **smooth** | `explore_nav_to_pose_smooth.xml`: each new NavFn path is smoothed in place by `smoother_server` (`SmoothPath`) | `nav2_params.yaml` |
| **tuned** | smoothing, as above | `nav2_params_tunnel.yaml`: `PathAlignCritic.offset_from_furthest` 20 → 8, `wz_std` 0.3 → 0.2 |

## Method
- **GUI runs** (Gazebo + both RViz windows), one at a time, interleaved: base, smooth, tuned,
  base, … RTF 1.00 in every run. 10 min of sim time from the first plan. Cave world, spawn
  (0, 0), TAD + DFS, NavFn.
- 2 runs per setup.
- The recorder logs at 10 Hz: pose in `map`; heading deviation from the path the controller
  follows (`/plan_smoothed` when smoothing, else `/plan`); corridor width from the LiDAR; and
  odometry `vx`, `wz`. It also saves the final map.

Definitions, fixed before the runs:

| Measure | Definition |
|---|---|
| Tunnel | LiDAR left + right clearance (±90°) < 1.2 m. Chambers are 2–6 m wide |
| Heading deviation | \|robot yaw − path direction at the nearest path point\|, while driving forward (vx > 0.05 m/s) |
| Turn reversals per m | sign changes of yaw rate between \|wz\| > 0.1 rad/s episodes, per metre driven in tunnels |
| Yaw per m | ∫\|wz\| dt in tunnels, per metre driven in tunnels |

Scripts, figures and per-run numbers are in `assets/tunnel_2026-10-18/`.

## Results
Mean, with the per-run values in brackets.

| In tunnels | base | smooth | tuned |
|---|---|---|---|
| Heading deviation, median | 8.0° (10.0 / 6.0) | 6.3° (3.9 / 8.7) | **3.3°** (3.1 / 3.4) |
| Heading deviation, p90 | 36.8° (38.6 / 35.0) | 28.6° (16.4 / 40.8) | **14.8°** (12.4 / 17.2) |
| Turn reversals per m | 1.05 (1.10 / 1.00) | 0.96 (0.91 / 1.01) | **0.69** (0.73 / 0.64) |
| Yaw turned per m | 67.6°/m | 63.4°/m | **54.1°/m** |
| Cross-track wobble (sd) | 1.9 cm | 2.6 cm | **1.2 cm** |

| Whole run | base | smooth | tuned |
|---|---|---|---|
| Explored area at 10 min | 46.2 m² (29.5 / 62.9) | **69.4 m²** (72.9 / 65.8) | 61.0 m² (57.0 / 65.1) |
| Goals reached / failed | 4.5 / 6.0 | **8.5 / 5.0** | 4.5 / 5.0 |
| "Failed to make progress" | 14.0 | **9.5** | 14.0 |
| BackUp recoveries | 4.5 | **3.0** | 5.5 |
| Path kinks > 30° per m (followed path) | 1.14 | **0.27** | 0.70 |

![[tunnel_metrics.png]]
*Bars are means and dots are runs. On the three tunnel measures (top row), every tuned run is
better than every base run.*

![[tunnel_deviation_run1.png]]
![[tunnel_deviation_run2.png]]
*The driven path coloured by heading deviation; thick segments are inside a tunnel. Run 1 and
run 2 of each setup.*

![[tunnel_area.png]]

### Every run on the map
Path coloured by time; goals reached (green) and failed (red), numbered in order; BackUp (▼).

![[tunnel_traj_base_1.png]]
![[tunnel_traj_base_2.png]]
![[tunnel_traj_smooth_1.png]]
![[tunnel_traj_smooth_2.png]]
![[tunnel_traj_tuned_1.png]]
![[tunnel_traj_tuned_2.png]]

## Explanation
- **The MPPI change does the straightening.** With `offset_from_furthest` at 20, `PathAlignCritic`
  only scored when a sample reached 0.54 m along the path, which MPPI's 0.56 m reach almost never
  allowed. At 8 (about 0.2 m) it scores in every cycle and holds the robot on the path line.
  Together with less angular sampling noise (`wz_std` 0.2), the p90 heading deviation fell from
  37° to 15° and turn reversals fell by a third. Smoothing alone barely moved deviation
  (28.6° p90, with one run as bad as base), so most of the gain is MPPI's.
- **Smoothing helps exploration, not straightness.** It removed most of NavFn's kinks (1.14 →
  0.27 per m) and had the fewest progress failures and the most area. But in tunnels Jazzy's
  simple smoother stops as soon as a smoothing step would enter inscribed cost. In the first
  (invalid, see below) runs it removed only about 40 % of the kinks there.
- **Tuned doesn't explore more than smooth** (61 vs 69 m², 14 vs 9.5 progress failures). Holding
  the path line more tightly may cost progress where the path hugs rocks. With 2 runs this is
  within the spread.

## Found along the way
- **Stale-path bug in the first smoothing BT (fixed, fc2c527).** The planner wrote `{raw_path}`
  and the smoother wrote `{path}`. When planning failed, `ComputePathToPose` cleared
  `{raw_path}`, but `{path}` kept the previous path, whose end was next to the robot. FollowPath
  then "reached" it, the coordinator never blacklisted the unreachable frontier, and sent it
  again: 25 times in the first `smooth_1`, from minute 6.4. The tree now smooths `{path}` in
  place. All four first smoothing runs were discarded and re-run; they are kept in the scratch
  run folder as `invalid_stale_path/`.
- One GUI launch never spawned the robot (no `odom`; Gazebo exited after 2.5 min). The recorder
  now gives up after 240 s without a plan.

## Verdict (pending confirmation)
For the goal of this test, straighter driving in tunnels, **tuned** (smoothing + PathAlign
offset 8 + `wz_std` 0.2) is clearly best: tunnel heading deviation −59 % (median) and −60 %
(p90), turn reversals −34 %, consistent in both runs. **smooth** is best on exploration
outcomes. n = 2 per setup.

## Next
- More runs, to see whether tuned's exploration matches smooth's.
- MPPI tuning without smoothing, to separate the two effects.
- The progress failures (9.5–14 per run) remain, because MPPI still stalls where the path hugs
  rocks ([[Path tracking and stalls 2026-10-18]]).
