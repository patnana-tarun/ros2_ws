---
tags: [issue]
---
# Full comparison 2026-10-19

The three setups from [[Tunnel tracking 2026-10-18]], each run until the cave is explored, with the
coordinator's new 30 s stall give-up switched on in every run. GUI runs, 3 per setup. Branch
`exp/tunnel-tracking`. Raw data: `~/full_runs_2026-10-19/`. Figures, metrics (CSV and JSON) and
scripts: `assets/navigation/full-comparison/`.

## Setups
| Setup | BT | MPPI |
|---|---|---|
| **base** | `explore_nav_to_pose.xml` | `nav2_params.yaml` |
| **smooth** | `explore_nav_to_pose_smooth.xml` (NavFn path smoothed in place) | `nav2_params.yaml` |
| **tuned** | smoothing, as above | `nav2_params_tunnel.yaml` (PathAlign offset 8, `wz_std` 0.2) |

All three: `stall_timeout:=30` (explore_coordinator gives up on a goal when the robot moved less
than 0.3 m in 30 s; 3a7ace6).

## Stop rules (fixed before the runs)
1. coverage ≥ 90 % of the true cave floor (84.4 m², generator `field.npz`; the same measure as
   [[Baseline runs 2026-10-08]])
2. coverage ≥ 75 % and less than 0.5 m² gained in 3 min: finished except for unreachable spots
3. 40 min of sim time (never reached)

Below 75 %, a trap doesn't end the run. That replaces the any-time 3-min rule of
[[Run to 90 percent 2026-10-18]], under which early traps ended 4 of 6 runs.

Definitions are in `analyze_full.py`:
- **stuck:** net movement under 0.5 m over the surrounding 60 s
- **tunnel:** LiDAR left + right clearance under 1.2 m
- **tunnel tracking:** measured only while driving forward in a tunnel and not stuck

## Results
Per-run values in brackets. With 3 vs 3, the smallest possible two-sided Mann-Whitney p is 0.10.

**Tunnel driving**

| | base | smooth | tuned |
|---|---|---|---|
| Heading deviation, median | 6.4° (3.7 / 6.1 / 9.3) | 4.2° (6.4 / 4.1 / 2.2) | **3.0°** (2.9 / 3.1 / 2.9) |
| Heading deviation, p90 | 28.0° (18.3 / 30.0 / 35.7) | 23.2° (32.7 / 22.1 / 14.7) | **13.3°** (17.1 / 11.1 / 11.8) |
| Turn reversals per m | 0.88 | 0.73 | **0.62** |
| Yaw turned per m | 69.9°/m | 50.1°/m | **42.4°/m** |
| Side-to-side wobble (sd) | 2.1 cm | 2.5 cm | **1.1 cm** (all 3 below every other run) |

**Pooled with the 2026-10-18 rounds** (tunnel p90 heading deviation, 7 runs per setup): tuned
9–18° against base 17–39°, **p = 0.006**; tuned against smooth, **p = 0.02**; smooth against base,
p = 0.80.

**Exploration**

| | base | smooth | tuned |
|---|---|---|---|
| Reached 90 % | 3 of 3 | 2 of 3 (one stuck at 86 %) | 2 of 3 (one stuck at 80 %) |
| Time to 90 % | 14.6 min (13.9 / 12.9 / 16.8) | **9.1 min** (10.5 / 7.6) | 12.2 min (15.3 / 9.0) |
| Coverage at 10 min | 73 % (77 / 81 / 61) | **89 %** (90 / 86 / 90) | 84 % (82 / 90 / 81) |
| Time stuck | 12.4 % | **4.7 %** | 7.4 % |
| Goals given up | 10.7 | **4.3** | 6.0 |
| BackUp per 10 min | 4.8 | **2.2** | 3.7 |
| Time lost per given-up goal | 46 s | 49 s | 48 s |

![[full_tracking.png]]
![[full_outcome.png]]
![[full_coverage.png]]

### Heading deviation along the driven path, one round per figure
![[full_deviation_round1.png]]
![[full_deviation_round2.png]]
![[full_deviation_round3.png]]

### Where the robot got stuck
![[full_traps.png]]
*Every stuck episode longer than 30 s, from all 9 runs. The F approach (13.6, −4.7) and the
chamber B rocks (3.7–5.7, 4.0) recur.*

### Run cards: trajectory and metrics of every run
![[full_card_base_1.png]]
![[full_card_base_2.png]]
![[full_card_base_3.png]]
![[full_card_smooth_1.png]]
![[full_card_smooth_2.png]]
![[full_card_smooth_3.png]]
![[full_card_tuned_1.png]]
![[full_card_tuned_2.png]]
![[full_card_tuned_3.png]]

## Reading
- **Straighter tunnel driving: tuned, now beyond doubt.** Tunnel heading deviation is roughly
  halved, and side-to-side wobble is halved. Pooled over 7 runs per setup it is significant
  (p = 0.006). The cause is MPPI's `PathAlignCritic` actually scoring (offset 8) plus less angular
  sampling noise. Smoothing alone doesn't straighten the robot (p = 0.80 against base).
- **Fastest exploration: smooth.** It had the most coverage at 10 min (all 3 runs above all 3 base
  runs), the fastest time to 90 %, and the fewest stuck minutes, given-up goals and BackUps. With 3
  runs each that is a consistent trend (p = 0.10, the floor for 3 vs 3), not proof.
- **Tuned sits between the two on exploration** (84 % at 10 min). Its run 3 stopped stuck at 80 %
  among the chamber B rocks. Holding the path line tightly may cost a little where the path hugs
  rocks.
- **The 30 s give-up** fired 2–12 times per run and cut the median time lost per given-up goal from
  60 s ([[2026-10-18]]) to 46–49 s. Goals that keep moving slowly still run to the 60 s timeout.
- **With the 75 % gate, no run was cut short by an early trap.** Base still spent the most time stuck
  (12 %).

## Verdict (pending the user's confirmation)
- For the stated goal, less heading deviation and fewer random turns in tunnels: **tuned**
  (smoothing + PathAlign offset 8 + `wz_std` 0.2).
- For exploration speed: **smooth**, with tuned close behind.

A possible next step is to take tuned's MPPI settings with a `wz_std` between 0.2 and 0.3, aiming to
keep the straightness and recover smooth's speed.

All figures of this note, each with a one-line meaning: [[Full comparison figures]].
