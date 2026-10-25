---
tags: [issue]
---
# Tunnel-reverse 2026-10-20

The user's idea, following [[Reverse-out 2026-10-20]]: reverse **only inside tunnels**. Once out
in open space, where there is room, turn round and explore forward as usual instead of carrying
on backwards. Branch `exp/tunnel-reverse` (1d68307, from tag `nav-reverse-v1`; fixes e271dac, aa50154). Raw data:
`~/tunnelrev_runs_2026-10-20/`. Figures, numbers and scripts: `assets/navigation/tunnel-reverse/`.

## Set-up
`ros2 launch explorer_exploration tunnel_reverse.launch.py` (bringup defaults unchanged). Same as
reverse-out (demo planner fixes, smoothing BT, pre-check, explored map, 30 s give-up, track 0.38),
plus:

| Part | What it does |
|---|---|
| `drive_mode_switcher` node | Passage width from the LiDAR = nearest return within ±10° of left (+90°) plus right (−90°). Width < 1.2 m for 1 s → **tunnel**; > 1.8 m for 1 s → **open** (in between: keep the mode). Publishes the controller name on `/controller_selector`, which the BT's ControllerSelector reads |
| Two MPPI controllers (`nav2_params_tunnel_reverse.yaml`) | `FollowPathReverse` (tunnel) = reverse-out's controller, unchanged. `FollowPath` (open) = the demo controller with `vx_min` 0.0: it can't reverse, so it turns round |
| Rotation counts as progress | `PoseProgressChecker` (`required_movement_angle` 0.5 rad) instead of `SimpleProgressChecker`, and the coordinator's give-up check `stall_angle` 0.5 rad. Without it, a goal behind the robot was given up halfway through the U-turn (smoke test 2) |

Smoke tests (4 min): with forward-only `vx_min` −0.1, the open-space controller still reversed;
`vx_min` 0.0 fixed that. After counting rotation as progress, the first goal (behind the robot)
was reached after one U-turn, and coverage at 4 min went from 26 % to 33 %.

## Round 1 results (3 GUI runs, same protocol: 90 %, stuck above 75 %, 40 min cap)
| | reverse-out (n = 4) | **tunnel-reverse** run 1 | run 2 | run 3 |
|---|---|---|---|---|
| Reversing in open space (share of samples) | 25–36 % | **0 %** | **0 %** | **0.7 %** |
| Reversing in tunnels | 12–46 % | 11 % | 13 % | 14 % |
| Turning on the spot in open space | 0 % | 4 % | 7 % | 4 % |
| Spins (≥ 300° in 60 s) | 0 | **0** | **0** | **0** |
| Start-up turning (goal behind) | 3–14° | 217° | 196° | 187° |
| Large open-area deviations | 0–14 % (mean 3.9) | 2.6 % | 0 % | 4.5 % |
| Heading p90, open areas | 6–82° (mean 28) | 23° | 18° | 22° |
| Cross-track p90, open areas | 2.8–5.8 cm | 6.4 cm | 7.3 cm | 8.2 cm |
| Heading p90 / cross-track p90, tunnels | 12–16° / 3.1–3.5 cm | 16° / 3.7 cm | 12° / 2.9 cm | 17° / 3.4 cm |
| Goal success | 53–79 % | 61 % | 65 % | 53 % |
| Time stuck | 3–21 % | 20 % | 26 % | 27 % |
| Coverage / time to 90 % | 88–90 %, 9.6–13.8 min (3 of 4) | 86 % | 84 % | 78 % |
| How it ended | 90 % (3), stuck (1) | wedged, C-F end | wedged, C-F end | wedged, east pocket |

![[tr_card_2.png]]
*Run 2: forward everywhere it had room, clean paths. It ended wedged at the C-F tunnel end (13.6, −4.2).*

![[tr_card_3.png]]
![[tr_card_1.png]]
![[tr_traps.png]]
*Where each setup got stuck. The east pocket (about 14–15, 4) traps every setup. The C-F end
trapped tunnel-reverse.*

![[tr_tracking.png]]
![[tr_coverage.png]]

## Round 1 reading
- **It behaves as asked.** In open space the robot no longer drives backwards (0–0.7 % against
  25–36 % for reverse-out). It turns round and drives forward. It still reverses inside tunnels
  (11–14 %). No spins in any run. In tunnels, path tracking is the same as reverse-out's.
- **Open-area tracking is a little worse than reverse-out's.** Heading p90 is 18–23°, against
  6–13° in reverse-out runs 1–3. Run 4 (82°) was the right-angle arcing case and pulls
  reverse-out's mean up to 28°. Cross-track p90 is 6–8 cm against 3–6 cm. Large deviations are
  0–4.5 % against 0–1.1 % (run 4: 14 %). All stay under the 10 cm limit at p90. Likely cause:
  the forward controller has to swing round onto paths that leave behind or beside the robot,
  where reverse-out simply backed onto them.
- **The price is turning on the spot again.** The start-up U-turn is about 200°, against 3–14°
  for reverse-out, and 4–7 % of open-space time is spent turning on the spot. That is the U-turn
  the user asked for, not spinning (no ≥ 300° events).
- **None of the 3 runs reached 90 %.** Each spent its last 3 minutes wedged in a passage
  0.55–0.85 m wide (0.33 m at the narrowest point in run 3), until the stuck rule stopped it.
  The robot had driven forward into a narrowing passage toward a frontier, with the tunnel
  (reverse) controller active. After that:
  - The explorer gave up those frontiers and sent goals back out, toward (5.8, −4.6), (7.5,
    −3.7) and (8.5, −3.1). The planner found valid paths starting 1–2 cm from the robot, leading
    out behind it.
  - The reverse controller still commanded almost nothing: |vx| < 0.03 m/s and |wz| < 0.1 rad/s
    for over a minute. BackUp failed with "Collision Ahead".
- **The trap is in the reverse-out controller, not in the switching.** The tunnel controller is
  identical to reverse-out's (checked parameter by parameter). Reverse-out run 1 ended the same
  way, in the B-E tunnel at 0.74–0.94 m width, moving 0.00 m in 30 s on a goal. Reverse-out
  usually reached 90 % before it needed those tunnel ends; tunnel-reverse explored in a
  different order and reached them earlier. Why MPPI stands still there is not yet known.
  Likely: every sampled move scores worse on the cost critics than standing still. Not verified.

## Why the planner sent the robot into gaps it couldn't turn in
NavFn plans for a point. It blocks only cells closer to a wall than the inscribed radius of the
footprint (half the width, 0.11 m), so any gap wider than about 0.25 m counted as passable. The
robot needs about 0.39 m (its diagonal) to turn round. Measured on the final maps (passage ≈ 2 ×
distance to the nearest wall):

| Run | Gap where it stopped | Narrowest gap on the last 1.5 m in |
|---|---|---|
| 1 | 0.67 m | 0.41 m |
| 2 | 0.71 m | 0.50 m |
| 3 | 0.41 m | 0.30 m |

Run 3's 0.30 m squeeze was too tight to manoeuvre in. In runs 1–2 there was room, and the
stand-still was the controller's.

## Fixes (both only in `tunnel_reverse.launch.py`; bringup defaults unchanged)
| Fix | Commit | What |
|---|---|---|
| Plan for a bigger robot | e271dac | Global costmap `robot_radius` 0.22 m instead of the footprint (inflation 0.22 → 0.35 m, keeping the cost band). NavFn no longer plans through gaps under about 0.45 m. The local costmap keeps the real footprint, so the controller can still squeeze through |
| Back out along the own track (retrace) | e271dac, aa50154 | `explore_coordinator` records the track every 5 cm (last ~20 m). When stuck in a tunnel (`/controller_selector` = FollowPathReverse), it drives 1 m back along that track with a simple pure-pursuit at 0.08 m/s on `/cmd_vel_nav`, so the velocity smoother and collision monitor still apply. It reverses if the robot came in forwards, and vice versa. Stops after 1 m, if blocked 6 s, or after 30 s |
| Retrace trigger (aa50154) | | A stall give-up in which the robot moved **< 0.1 m** in 30 s, or 2 failed goals at one spot (planner or pre-check failures). Loop guard: no new retrace starting within 0.5 m of the last one for 300 s |

The first trigger (e271dac) retraced after **every** stall give-up. In run 3 of that round, at the
0.55 m gap at the chamber-B mouth (3.4, 3.1), the robot crept 0.24–0.30 m per 30 s (all setups
creep there, 0.03–0.07 m/s), gave up just under the 0.3 m limit, and backed out 1 m: 39
retraces in 36 min, 30 % coverage at the 40 min cap. The < 0.1 m trigger and the loop guard
(aa50154) fix this: in the wedges the robot had moved 0.00–0.09 m, and creeping is progress.

## Results after the fixes (3 GUI runs each)
| | reverse-out (n = 4) | tunnel-reverse (round 1) | + radius + retrace (every stall) | **+ radius + guarded retrace** |
|---|---|---|---|---|
| Reached 90 % | 3 of 4 (9.6–13.8 min) | 0 of 3 | 1 of 3 (16.0 min) | **2 of 3 (16.6, 21.2 min)** |
| Final coverage | 88–90 % | 78–86 % | 30 / 84 / 91 % | 81 / 90 / 91 % |
| Ended wedged | 1 of 4 | 3 of 3 | 0 (1 retrace loop) | **0** |
| Spins (≥ 300° in 60 s) | 0 | 0 | 0 / 0 / 1 | 0 / 1 / 0 (Nav2 Spin recovery) |
| Reversing in open space | 25–36 % | 0–0.7 % | 0.6–1.6 % | 1.3–2.9 % |
| Large open-area deviations | 0–1.1 % (run 4: 14 %) | 0–4.5 % | 1.8–5.4 % | **0.4–2.1 %** |
| Heading p90, open areas | 6–13° (run 4: 82°) | 18–23° | 18–22° | 13–20° |
| Cross-track p90, open areas | 2.8–5.8 cm | 6.4–8.2 cm | 5.6–7.0 cm | 5.4–6.7 cm |
| Heading p90, tunnels | 12–16° | 12–17° | 13–19° | 14–21° |
| Cross-track p90, tunnels | 3.1–3.5 cm | 2.9–3.7 cm | 2.8–4.7 cm | 4.0–4.5 cm |
| Time stuck | 3–21 % | 20–27 % | 14–60 % | 10–33 % |
| Goal success | 53–79 % | 53–65 % | 9–59 % | 55–60 % |
| Retraces per run (finished) | – | – | 4 / 3 / 39 | 2 / 6 / 6 (13 of 14 "done", 1 ended by a goal timeout) |
| Retrace: distance from own track, p90 | – | – | 0.5–4.4 cm | **1.9–2.6 cm** |

Retrace time (plus 3 s after it, until the next goal's path arrives) is left out of the
path-tracking rows: Nav2's path is stale then. The retrace row measures it against the last 20 m
the robot drove instead.

![[trg_card_1.png]]
*Guarded retrace, run 1: 90 % in 16.6 min.*

![[trg_card_3.png]]
![[trg_card_2.png]]
*Run 2 was not trapped: it stopped at 81 % because nothing new was in reach for 3 min (the stop
rule), after the C-F fan and the east pocket frontiers were refused as too narrow.*

![[trr_card_3.png]]
*Retrace after every stall: 39 back-and-forth retraces at the chamber-B mouth.*

## Reading (after the fixes)
- **The wedges are gone.** No run of the guarded version ended stuck in a tight passage. The
  bigger planning robot keeps paths out of gaps under about 0.45 m, and where the robot still
  stood still (5 times, moved 0.00–0.09 m in 30 s), the retrace backed it out. It held its own
  track within 2–3 cm.
- **The retrace must not fire when the robot is only slow.** Backing out after every give-up
  undid the progress at a slow squeeze (39 retraces, 30 % coverage). The < 0.1 m trigger and the
  loop guard fixed this. The guard fired 14 times in 3 runs.
- **Path accuracy:** open-area tracking improved over round 1 (large deviations 0.4–2.1 %,
  heading p90 13–20°). It is still behind reverse-out's best runs (6–13°). Tunnel cross-track p90
  grew from about 3.4 to 4.0–4.5 cm. Likely cause: the larger inscribed zone moves paths
  around rocks, so there are more bends. Not verified.
- **Speed:** 90 % in 16.6–21.2 min, against 9.6–13.8 min for reverse-out. U-turns at start-up
  (about 200°) and turning on the spot in open areas (5 %) cost time. Reverse-out avoids both by
  driving backwards.

**Verdict (pending the user):** the guarded version does what the user asked (forward in open
space, reverse in tunnels) and no longer gets wedged: 2 of 3 runs reached 90 %, and the third
was not stuck. Reverse-out is still faster and tracks slightly better. The fixes themselves
(planner radius, guarded retrace) could also help reverse-out, which got wedged once in 4 runs.
Not added to [[Comparisons]].

## Open
- Try the planner radius and the guarded retrace on reverse-out (one config change and two
  launch arguments).
- Why MPPI stands still in tight passages with a valid path behind it ([[Known limitations]]
  #26). The retrace works around it, but doesn't explain it.
- Hysteresis between 1.2 and 1.8 m keeps the previous mode. In run 2 of round 1, the forward
  controller was still active at 1.5 m width on the way into C-F (1 s dwell); it switched at
  1.0 m.
- The robot's own track is only "known free" if nothing moved. On the real robot, the collision
  monitor is what protects the retrace.

All figures of this note, each with a one-line meaning: [[Tunnel-reverse figures]].
