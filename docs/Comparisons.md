---
tags: [moc]
---
# Comparisons

Every design decision that was settled by comparing options, with the chart that decided it.
Built for the presentation and the report.

> **Rule:** a comparison is added here only once its analysis is finished and the result is
> confirmed. Work in progress stays in its issue note and the daily log. Each entry links to the
> note that holds the method and the full numbers. Charts are drawn by
> `assets/comparisons/make_figures.py` from the numbers in those notes.

## At a glance
| # | Question | Options compared | Chosen | Deciding number | Evidence |
|---|---|---|---|---|---|
| 1 | Which frontier to explore next? | global TAD · DFS · DFS + shadow filter | **DFS + shadow filter** | finished the cave: 78.0 m² (94 %) in 23 min | 1 run each |
| 2 | Which local controller? | Regulated Pure Pursuit · MPPI | **MPPI** | RPP never turned round with the goal behind | observed |
| 3 | Skid-steer track width in the sim | geometric 0.176 m · effective 0.50 / 0.43 m | **0.43 m** | yaw rate 0.35× → 0.90–1.08× of command | measured |
| 4 | How to estimate yaw? | wheels only · EKF wheels + gyro | **EKF** | 83° vs true 82°; wheels alone 184° | 1 turn test |
| 5 | Which end leads over rocks? | bogie first · rocker first | open | rocker-first: 8 cm one-sided rock vs 6 cm | sim only |
| 6 | Inflation and recovery order | 0.30 m, old BT · 0.22 m, old BT · 0.22 m, BackUp first | **0.22 m + BackUp first** | 4 goals vs 2 in 5 min | 1 run each |
| 7 | How often to replan? | every 1 s · keep 10 s · keep 4 s | **keep 4 s** | 1 s flipped paths; 10 s missed side passages | observed |
| 8 | EKF output rate | 10 Hz · 30 Hz | **30 Hz** | startup overshoot 140° → 55°, no multi-turn spins | 3 + 6 runs |
| 9 | Starting SLAM and Nav2 | autostart · CLI call after 8 s · startup node | **`lifecycle_startup` node** | 12/12 launches came up vs 7/8 | 28 launches |
| 10 | Where to thin TF for the mesh? | at the sources · in the relay | **in the relay** | robot keeps 100 /s, mesh gets 33 /s | measured |
| 11 | Which GPU renders the sim? | Intel iGPU · RTX 4060 (PRIME offload) | **RTX** | CPU busy 29 % → 11 %; nav metrics unchanged | 1 run each |
| 12 | Which global planner? | NavFn · Smac Lattice (+ pre-check, + wide inflation) | **NavFn** | Smac: paths −47 % turning, but area −16 %, 2.4× recoveries | 6 runs each |
| 13 | Does a repeater extend the mesh? | direct link · via the Pi Zero repeater | **only behind obstacles** | worked into a room (2 hops); not in line of sight | 3 walk tests |

---

## 1. Frontier selection
![[cmp_frontier_selection.png]]
TAD as written adds the normalised distance, so it favours the farthest frontier and leaves
branches half-done. Depth-first selection keeps the robot in its current branch. Without the
filter, it then toured every rock's LiDAR shadow (minutes 10–25). With frontiers bordering less
than 1 m² of unknown skipped, it was the first run to finish the cave.
![[slam_map_cave_dfs.png]]
*The finished DFS map: all six chambers, three dead ends, both loops.* Details:
[[Frontier exploration]].

## 2. Local controller
Regulated Pure Pursuit was tried first because it is lighter. With the goal directly behind the
robot, its rotate-in-place flipped direction every cycle and the robot never turned round, which
is common at a dead end. MPPI with a TwirlingCritic doesn't flip. Details: [[Navigation stack]].

## 3. Skid-steer calibration
![[cmp_track_width.png]]
Turning on the spot, a skid-steer's wheels slide sideways, so the geometric track width gives
only about a third of the commanded turn. An effective width corrects this. After the chassis was
flipped and the stall-torque limit set, 0.43 m. Details: [[Gazebo simulation]].

## 4. Yaw estimation
![[cmp_odometry_fusion.png]]
The wheels slip when the robot pivots, so wheel odometry alone more than doubles the turn. The EKF
takes yaw rate from the gyro instead. After a further 1 m leg, the EKF position was within 5 cm.
Details: [[Odometry fusion]].

## 5. Rock climbing
![[cmp_rock_climbing.png]]
Both layouts cross about 5 cm (1.5 × wheel radius) under both tracks. Rocker-first crosses taller
one-sided rocks, likely because the rigid rocker wheel is pushed up and over by the bogie behind
it. The robot still leads with the bogie. Decide on the real robot. Details: [[Rock climbing]].

## 6. Inflation and recovery order
![[cmp_inflation_bt.png]]
With 0.30 m inflation the robot wedged between rock halos. With a 30 s progress timeout, the
coordinator's goal timeout always fired before BackUp ever ran. Thinner inflation, BackUp as the
first recovery and a 15 s progress timeout doubled the goals reached in the same 5 min. Details:
[[Navigation stack]], [[2026-10-05]].

## 7. Replanning interval
Replanning every 1 s (Nav2's default tree) made the path flip sides around rocks, so the robot
kept turning. Keeping each path for 10 s held the robot on its first route after a better side
passage had appeared. 4 s, with immediate replanning if the path gets blocked, is the compromise.
Details: [[Navigation stack]].

## 8. EKF output rate
![[cmp_ekf_rate.png]]
At 10 Hz (tried for the mesh relay), the startup turn to a goal behind the robot overshot by 140°
on average and spun about 4 full turns in 2 of 3 runs. At 30 Hz: 55° and no multi-turn spin. Each
dot is one run. The remaining ~65–87° overshoot is still open. Details:
[[Baseline runs 2026-10-08]], [[Relay rates]].

## 9. Startup hang
![[cmp_startup_hang.png]]
Nav2 and SLAM sometimes stuck at "Configuring", because a lifecycle reply was dropped when a
client called before discovery had matched. A node that creates its clients at launch and calls
once after 8 s came up 12 times out of 12, at the cost of about 6 s of startup. Details:
[[Nav2 not loaded]].

## 10. TF rates on the robot and the mesh
![[cmp_tf_rates.png]]
Thinning TF at the sources (10–15 Oct) cut the mesh load but starved the EKF, causing the 140°
overshoot in #8. Now the robot runs at full rate and the relay forwards 1 of every 3 messages per
source: the same 33 /s on the mesh. SLAM's rate is the midpoint of the measured 50.0–53.3 /s.
Details: [[Relay rates]].

## 11. Rendering GPU
| | Intel iGPU (default, PRIME on-demand) | RTX 4060 (offload variables) |
|---|---|---|
| GPU load | RTX 0 % | RTX 34 %, 671 MiB |
| Whole-CPU busy | 29 % | 11 % |
| Controller loop, warnings | 6.6–13.9 Hz, 5 | 7.1–10.9 Hz, 5 |
| Real-time factor | 1.00 | 1.00 |

Moving rendering to the RTX frees the CPU but doesn't change navigation: rendering wasn't the
bottleneck. The "7 Hz" warnings turned out to be the first cycle after a costmap clear
([[Path tracking and stalls 2026-10-18]]). Details: [[2026-10-18]].

## 12. Global planner
![[cmp_planner_pooled.png]]
Smac Lattice checks the real rectangular footprint and only joins drivable motions. Its paths turn
half as much and have no kinks (p ≤ 0.004). But its 0.5 m / 16-heading lattice can't thread the
chamber B entrance or the B–E tunnel, so some runs lose a whole branch of the cave. It also needs
more BackUps and Spins (p = 0.03). Neither the planner pre-check nor wider inflation fixed that.
![[planner_ab_area.png]]
![[planner_followup_arms.png]]
Details: [[Planner comparison 2026-10-18]], [[Planner follow-ups 2026-10-18]].

## 13. Mesh repeater
| Test | Route | Result |
|---|---|---|
| 1 | straight line, line of sight | no gain: packets went direct or not at all |
| 2 | L-shape into a room, repeater at the door | **worked**, 2 hops, normal metrics |
| 3 | L-shape in the open | route kept flipping between direct and via the repeater |

A repeater helps only where an obstacle kills the direct link. Then BATMAN has one route, and it
goes through the repeater. Distances and TQ weren't recorded, so the explanations are not yet
verified. Details: [[Relay field tests 2026-10-17]], [[Relay placement protocol]].
