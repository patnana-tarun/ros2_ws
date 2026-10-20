---
tags: [issue]
---
# Reverse-out 2026-10-20

The user's idea: when the goal is behind, **back out along the path** instead of turning on the
spot; no 360° turns unless necessary. If a direction change is needed, do a three-point turn
(reverse curving one way, then forward curving the other). Branch `exp/stuck-ablation`
(42ff5b5). Raw data: `~/ablation_runs_2026-10-20/`. Figures and numbers:
`assets/reverse_2026-10-20/`. Follows [[Stall ablation 2026-10-20]].

## Setups (all: demo planner fixes, smoothing BT, pre-check, explored map, 30 s give-up, track 0.38)
| Setup | File | MPPI changes vs `nav2_params_demo.yaml` |
|---|---|---|
| **Reverse-out** | `config/nav2_params_reverse.yaml` | `PathAngleCritic.mode` 0 → 1 (may follow the path forward or backward), `PreferForwardCritic` weight 5 → 2, `vx_min` −0.1 → −0.15. On-the-spot turns still allowed |
| **Three-point turn** | `config/nav2_params_kturn.yaml` | the same + `motion_model: Ackermann`, `min_turning_r` 0.2: MPPI may not turn on the spot |

2 GUI runs of reverse-out and 1 of the three-point turn, as the user asked. Same protocol as
[[Full comparison 2026-10-19]] (90 % coverage, stuck above 75 %, 40 min cap).

## Results
| | before (rerun) | kept version (0.34) | **reverse-out (0.38)** | three-point turn (0.38) |
|---|---|---|---|---|
| Runs | 3 | 3 | 2 | 1 |
| Spins (≥ 300° in 60 s, per run) | 3.7 | 0 | **0** | 0 |
| Start-up turning (goal behind) | 185° | 43° | **8°** | 2° |
| On-the-spot turning (share of commands) | 3 % | 0.5 % | **0.02 %** | 0.4 % |
| Reversing (share of commands / distance per run) | 10 % / 4 m | 12 % / 5 m | 23 % / 10 m | 23 % / 14 m |
| Large open-area deviations | 8 % | 0.9 % | **0.55 %** | 8 % |
| Heading p90 in open areas | 25° | 17° | **11°** | 22° |
| Heading p90 in tunnels | 17° | 15° | 15° | 13° |
| Time stuck | 17 % | 31 % | **12 %** (19 / 5) | 30 % |
| Goal success | 36 % | 31 % | **65 %** | 56 % |
| Coverage reached | 80–90 % | 89–91 % | 88 % / 90 % (10.1 min) | 77 % |

**While reversing**, the robot holds the path as well as or better than when driving forward:
cross-track p90 2.8–3.0 cm (forward 3.7–3.8 cm), heading within 10° of the reversed path
direction (p90).

![[rev_card_rev38_2.png]]
*Reverse-out, run 2: a clean path with no loops, 90 % in 10.1 min, stuck 5 % of the time.*

![[rev_card_rev38_1.png]]
![[rev_card_kturn38_1.png]]
![[rev_tracking.png]]
![[rev_coverage.png]]
![[rev_traps.png]]

## Reading
- **Reverse-out removes the need to turn round.** The robot backs toward a goal behind it
  (start-up turning 8°) and backs out of dead ends. Turning on the spot almost disappears (0.02 %
  of commands), and with it the overshoot. Path accuracy and stuck time both improve: the
  trade-off of [[Stall ablation 2026-10-20]] goes away.
- **The three-point turn doesn't happen with MPPI alone.** MPPI looks only 2.8 s ahead, so it
  can't plan "reverse, then forward". Forbidden to turn on the spot, it keeps reversing (smoke
  test: 63 % reversing, top forward speed 0.03 m/s), stalls on direction changes, and reached
  only 77 %. A real three-point turn needs a planner that plans direction changes (Smac
  Hybrid-A* with reversing) or a scripted manoeuvre.
- Reversing relies on the 360° LiDAR and the collision monitor, which both cover the rear.

## Open
- **n = 2.** One more confirmation run is needed before this is called confirmed and added to
  [[Comparisons]].
- Whether forward is preferred enough over long distances: 23 % reversing is fine, but should
  not grow in open areas.
- On the real robot, reversing speed and the rear-facing behaviour need checking (reverse
  `min_duty` and encoders).
