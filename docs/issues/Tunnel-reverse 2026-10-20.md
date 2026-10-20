---
tags: [issue]
---
# Tunnel-reverse 2026-10-20

The user's idea, following [[Reverse-out 2026-10-20]]: reverse **only inside tunnels**. Once out
in open space, where there is room, turn round and explore forward as usual instead of carrying
on backwards. Branch `exp/tunnel-reverse` (1d68307, from tag `nav-reverse-v1`). Raw data:
`~/tunnelrev_runs_2026-10-20/`. Figures, numbers and scripts: `assets/tunnel_reverse_2026-10-20/`.

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

## Results (3 GUI runs, same protocol: 90 %, stuck above 75 %, 40 min cap)
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

## Reading
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

**Verdict (pending the user):** the switching works and keeps the open-area behaviour forward,
as asked. It is not better overall than reverse-out yet: it brings back a U-turn at start-up, and
3 of 3 runs ended wedged before 90 %. Fix the tight-passage stand-still first (see Open), then
compare again. Not added to [[Comparisons]].

## Open
- Reproduce the stand-still without a full run: put the robot at (13.6, −4.2) facing into the
  C-F end, send the goal (7.5, −3.7), and record MPPI's critic costs.
- Candidate fixes, path accuracy first:
  - (a) a retrace recovery that backs out along the robot's own recorded track (known to be
    free) when it stalls in a tunnel;
  - (b) MPPI cost-critic tuning for tight passages;
  - (c) keep frontier goals out of passages narrower than the robot can turn in.
- Hysteresis between 1.2 and 1.8 m keeps the previous mode. In run 2, the forward controller
  was still active at 1.5 m width on the way into C-F (1 s dwell); it switched at 1.0 m.
