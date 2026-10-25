---
tags: [issue]
---
# Navigation fixes 2026-10-19

Root-cause analysis of the four problems the user saw in RViz:
- drift in open areas
- trouble in the narrow tunnel
- red paths running through unknown space
- 360° turns

Then the fixes and two rounds of GUI validation. Branch `exp/tunnel-tracking`. **Interim:**
path tracking is fixed and verified; a stuck regression is open. Raw data:
`data/demo_runs_2026-10-19/` (first in `~/`, then `docs/` until 2026-10-25), `~/full_runs_2026-10-19/`. Scripts, figures and numbers:
`assets/navigation/navigation-fixes/`. Priority since 2026-10-19: following the path correctly first,
speed second.

## What the RViz lines are
In `nav2_default_view.rviz`:
- **red** = `/plan`, NavFn's raw global path (the smoothed `/plan_smoothed` is not shown)
- **blue** = `/local_plan`
- the yellow and green dotted lines are TF links from the robot back to the `odom` origin, not
  paths

## Root causes
Measured on the 9 runs of [[Full comparison 2026-10-19]] plus the validation runs.

| Symptom | Cause | Evidence |
|---|---|---|
| Drift in open areas | `PathAlignCritic` effectively off: it scores only past 0.54 m along the path, but trajectories reach 0.56 m. Tunnel walls hold the robot near the path; open space doesn't | 72 % of large open-area deviations (xte > 10 cm or heading > 30°) have no other trigger. Without tuning, 31–38 % of open-area driving deviated |
| Leaving the path near goals | MPPI hands over to `GoalCritic` 1.0 m before the goal and stops scoring the path | 17 % of large open-area deviations |
| Smoother | **not a cause**: smoothed and raw paths differ by 0–2 cm (median), max 4–19 cm | 6 runs |
| Narrow tunnel (B–E) | **not width**: every tunnel is ≥ 0.61 m (B–E 0.67 m; the robot needs 0.39 m to pivot). In B–E the cause was the weak tracking above: heading p90 31–33° and 286–309 s without tuning, 8.6° and 111 s with it | ground-truth `field.npz`, per-tunnel split |
| Red path through unknown space | NavFn `allow_unknown: true` costs an unknown cell 253 against 50 for free space, so it shortcut through unexplored space past any known route more than ~5× longer | up to 13.6 % of plans crossed ≥ 2 m of later-mapped rock (longest 8.6 m); 40–86 % at the F approach |
| "360°" turns | **Over-rotation, then a slow crawl back.** The robot turns 1.2–1.3× the commanded yaw rate (Gazebo true pose; the EKF heading matches the truth within 1°) and responds about 0.2 s late, so MPPI swings past the path heading (+65°), crawls back at 0.05 rad/s, then swings again | in nearly every event the robot was aligned first and then kept turning another 136–723°; 12 of 14 events happened during stalls and recoveries |
| Localization | not a cause: EKF/SLAM heading within 0.3–0.8° of the truth (median), map → odom yaw jumps ≤ 2–4° | validation runs |

## Changes (all on `exp/tunnel-tracking`)
| Change | File | Reason | Status |
|---|---|---|---|
| NavFn `allow_unknown: false` | `config/nav2_params_demo.yaml` | plan only through explored space | kept |
| Global costmap reads `/map_explored` | `nav2_params_demo.yaml` and `frontier_tad_node.py` (`publish_explored_map`) | the ray gaps the frontier node counts as explored would otherwise block the planner (a smoke run refused 2 of 4 reachable frontiers) | kept |
| Pre-check, 2 strikes | `explore_coordinator.py` (`precheck_path`) | refuse unreachable frontiers before any recovery runs; 1 failure can be a costmap that hasn't caught up at start-up (seen) | kept |
| Goal hand-over 1.0 → 0.5 m | `PathFollowCritic` and `GoalCritic` `threshold_to_consider` | the 17 % near-goal deviations | kept |
| Spin recovery removed | `explore_nav_to_pose_demo.xml` | — | **reverted**: stuck time 7 % → 31 % in round 1, and the rotation events did not drop. The attribution to Spin was a correlation, not a cause |
| Sim track width 0.43 → 0.34 | `explorer_gazebo.xacro` | over-rotation 1.25× | **ineffective**: a step test (no Nav2) gives the same steady turn rates at 0.43 (0.87–1.29×) and 0.34 (1.00–1.36×). The over-rotation is stick-slip, not a gain |

## Validation
GUI runs, same protocol as [[Full comparison 2026-10-19]]: stop at 90 % coverage, when stuck
above 75 %, or at 40 min. Before = tuned (smoothing + MPPI tuning, 3 runs). Round 1 = the first 4
fixes with Spin removed (3 runs). Round 2 = Spin back, track 0.34 (3 runs).

**Path tracking (the priority)**

| | before (tuned) | round 1 | round 2 |
|---|---|---|---|
| Large deviations in open areas | 7.1 % | 7.2 % | **3.2 %** |
| Heading p90 in open areas | 23.3° | 24.9° | **20.7°** |
| Heading p90 in tunnels | **13.3°** | 14.2° | 15.5° |
| Heading p90 in B–E | 17.6° | 20.6° | **12.9°** |
| Rotation events (≥ 300° in 60 s, < 1 m) | 2.7 per run | 2.7 | **0** |
| Turning at start-up (goal behind) | 214° | 217° | **41°** |
| Longest path stretch through not-free space | 3.9 m | 0.4 m | **0.6 m** |
| Unknown under a path at plan time (max) | — | 0.33 m | **0.23 m** (the goal's speckle) |

**Getting there**

| | before (tuned) | round 1 | round 2 |
|---|---|---|---|
| Reached 90 % | 2 of 3 | 2 of 3 | 2 of 3 |
| Time to 90 % | **12.2 min** | 28.0 min | 16.3 min |
| Time stuck | **7.4 %** | 30.9 % | 33.4 % |
| Goal success | **59 %** | 35 % | 39 % |

![[demo_tracking.png]]
![[demo_deviation_round2.png]]
![[demo_traps.png]]
*Round 2 also stalls in open areas (start chamber, chamber C), not only in dead ends.*

![[demo_card_demo2_1.png]]
![[demo_card_demo2_2.png]]
![[demo_card_demo2_3.png]]

## Open
Follow-up: [[Stall ablation 2026-10-20]].

- **Stuck regression (round 1 and round 2).** MPPI outputs near zero while valid paths exist.
  In round 2 its turn commands never exceeded 0.22 rad/s (before: 0.62). At start-up it reverses
  slowly toward a goal behind it instead of turning. The spins are gone, but so is decisive
  turning. Not yet isolated: allow_unknown/explored map, the 0.5 m hand-over and the sim
  track-width change all changed together. Next: one change per arm.
- Why the round-2 turn commands stay small, given the step test shows the robot can still turn
  at 0.64 rad/s.

All figures of this note, each with a one-line meaning: [[Navigation fixes figures]].
