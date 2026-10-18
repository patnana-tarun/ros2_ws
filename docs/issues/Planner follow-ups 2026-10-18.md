---
tags: [issue]
---
# Planner follow-ups 2026-10-18

Second benchmark, on branch `exp/planner-tuning`. It tests the two follow-ups proposed in
[[Planner comparison 2026-10-18]], and runs Smac and NavFn again under fresh conditions.

## Method
Four arms ran **side by side** in each of 3 rounds of 10 min (sim time). Otherwise the setup is
the same as [[Planner comparison 2026-10-18]]: cave, spawn (0, 0), TAD + DFS, headless, own
`ROS_DOMAIN_ID` and `GZ_PARTITION` per arm.

| Arm | Planner | Coordinator pre-check | Global-costmap inflation |
|---|---|---|---|
| navfn | NavFn | off | 0.22 m / 12 (control) |
| smac | Smac Lattice | off | 0.22 m / 12 |
| smacpc | Smac Lattice | **on** (`precheck_path:=true`) | 0.22 m / 12 |
| smacpcw | Smac Lattice | on | **0.35 m / 6** (`nav2_params_smac_wide.yaml`; local costmap unchanged) |

The pre-check asks the planner once before a frontier is sent. If there is no path, the
frontier is blacklisted at once and never reaches the navigator's recovery tree
(`explore_coordinator.py`). Four sims saturated the CPU (about 95 %), so the real-time factor was
**0.75** for every arm. That is equal across arms, but different from the first comparison.
Scripts and per-run data are in `assets/planner_followup_2026-10-18/`.

## Results
Mean ± sd over 3 runs.

| Metric | navfn | smac | smacpc | smacpcw |
|---|---|---|---|---|
| Explored area at 10 min (m²) | **68.9 ± 3.0** | 48.1 ± 17.2 | 63.5 ± 5.7 | 55.4 ± 24.9 |
| … per round | 71.4 / 69.7 / 65.6 | 36.5 / 67.9 / 39.9 | 68.2 / 65.1 / 57.2 | 74.2 / 27.2 / 64.8 |
| Stall time (s) | **84 ± 14** | 170 ± 91 | 101 ± 50 | 156 ± 159 |
| "Failed to make progress" | **4.0 ± 0.0** | 8.7 ± 4.9 | 8.0 ± 4.0 | 6.7 ± 7.2 |
| BackUp / Spin recoveries | **2.7 / 1.0** | 7.7 / 4.0 | 7.0 / 2.7 | 6.0 / 2.7 |
| Goals the planner refused (distinct) | **1.7** | 3.0 | 3.3 | 5.0 |
| … refused by the pre-check | — | — | 1.3 | 1.7 |
| Path kinks > 30° per m | 0.61 | **0.00** | **0.00** | **0.00** |
| Path turning (°/m) | 82 | 47 | **40** | 53 |
| Path footprint touching inscribed cost | **15 %** | 26 % | 21 % | 26 % |
| Time > 10 cm off path | 8.4 % | 14.9 % | 9.7 % | **7.3 %** |
| `planner_server` CPU (s) | **146** | 227 | 251 | 239 |

![[planner_followup_arms.png]]
*Dots are runs, bars are means. Only the path-shape panels separate cleanly. The outcomes
overlap, except that NavFn is the most consistent arm.*

**NavFn vs Smac, both benchmarks pooled** (n = 6 each; p from Mann-Whitney U):

| Metric | NavFn | Smac | Smac better in | p |
|---|---|---|---|---|
| Path kinks > 30° per m | 0.67 | 0.02 | 6/6 | 0.004 |
| Path turning (°/m) | 89.7 | 47.3 | 6/6 | 0.002 |
| Replans per min | 35.0 | 20.7 | 5/6 | 0.04 |
| "Failed to make progress" | 9.0 | 9.0 | 4/6 | 0.87 |
| Stall time (s) | 124 | 140 | 3/6 | 0.82 |
| Explored area at 10 min (m²) | 63.6 | 53.2 | 1/6 | 0.24 |
| BackUp recoveries | 4.0 | 7.3 | 0/6 | 0.03 |
| Spin recoveries | 0.8 | 4.0 | 0/6 | 0.03 |
| Time > 10 cm off path | 6.7 % | 11.5 % | 0/6 | 0.07 |

## Explanation
- **Where Smac gets stuck.** Every low-coverage Smac run (27–40 m²) ended with Smac refusing,
  10–14 times in a row, a frontier about 1–1.5 m ahead at one of two places:
  - from (3.5–3.8, 3.95) toward (4.8, 3.8–4.5): the chamber B entrance, where boulders 9 and 10
    leave narrow slots ([[Cave world]])
  - from (10.6, 5.9) toward (11.3–11.9, 5.3–5.5): the B–E tunnel, the narrowest in the cave
    (0.72 m nominal, rougher in places)

  The lattice only plans with 16 headings and 0.5 m-radius arcs. The real robot pivots at any
  angle and drives straight through, and NavFn's centre-line paths let it. So Smac sometimes cuts
  off a whole branch of the cave. That explains both its lower mean area and its larger spread.
  This mechanism is inferred, not verified pose by pose.
- **The pre-check helps Smac.** Against plain Smac it gained area (+32 %), cut stall time by 40 %
  and needed fewer spins, in 2 of 3 rounds. It only fired 1–2 times per run, though. Most refusals
  happen mid-route, when newly mapped rock blocks a goal that was reachable when it was sent, and
  a one-time check can't catch that. It doesn't lift Smac to NavFn's level.
- **Wider inflation didn't help.** It didn't keep paths further from rocks (inscribed-cost contact
  26 % vs 21 %). It raised the number of refused goals to 5 per run in every round, and its run 2
  collapsed to 27 m². The higher cost in narrow places seems to push Smac into refusing more.
  NavFn's paths actually touched the least inscribed cost of all arms (15 %).
- **NavFn was the most consistent arm:** 4 progress failures in every round, 66–71 m² explored.
  In the first comparison its progress failures varied from 8 to 22. The CPU load differed between
  the two benchmarks (2 sims vs 4), so the rounds can't be compared directly.

## Verdict
**Smac Lattice with the stock 0.5 m primitives is not adopted.** It produces much better-shaped
paths, which is significant at p ≤ 0.04. But it can't thread the cave's narrowest passages, so on
the outcomes that matter the robot does no better, and it needs significantly more recoveries.
Neither follow-up changed that. NavFn stays the planner.

The root causes in [[Path tracking and stalls 2026-10-18]] still stand. The next candidate keeps
NavFn's reach and fixes the path shape afterwards:
1. A `SmoothPath` step in the BT after `ComputePathToPose`. `smoother_server` already runs, and its
   simple smoother also fills in pose headings, which fixes the `IsPathValid` heading-0 issue.
2. `PathAlignCritic.offset_from_furthest` ≈ 8, so the critic engages within MPPI's 0.56 m reach.

A finer lattice (about 0.2 m radius, 32 headings) is a possible later test of Smac.

## Limitations
- 3 rounds per arm. Exploration order diverges early, so outcome metrics have a large spread.
  Only the path-shape results and the recovery counts reach p < 0.05.
- Real-time factor 0.75 here vs about 1 in the first comparison, so the two benchmarks are pooled
  only for NavFn vs Smac. Within each round all arms shared the same load.
- The clearance metrics read each arm's own global costmap. For `smacpcw` that costmap is more
  inflated, so only the inscribed-contact share is comparable across arms.
