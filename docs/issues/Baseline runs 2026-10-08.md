---
tags: [issue]
---
# Baseline runs 2026-10-08

Three unchanged GUI runs of the current exploration stack, observed passively. Nothing was
tuned or fixed. Raw data, scripts and every event snapshot: `~/baseline_runs_2026-10-08/`
(`runN/` with `pose.csv`, `cmd.csv`, `rosout.csv`, `goals.csv`, `coverage.csv`, `snaps/*.npz`,
`launch.log`, `analysis.md`, `trajectory.png`). Times below are **mm:ss of sim time** from the start
of each run (sim ran at real time, RTF 1.00).

## 1. Baseline configuration

- **Code:** commit `07f45b4` plus the uncommitted working tree on 2026-10-08: EKF 10 Hz,
  wheel TF 6.67 Hz, SLAM `transform_publish_period` 0.06 s, `map_update_interval` 3 s,
  [[Cave world]] with boulder 12 removed. Installed files checked identical to source.
- **Launch:** `ros2 launch explorer_exploration bringup.launch.py` with default arguments: Gazebo
  GUI (`cave.sdf`), both RViz windows, SLAM Toolbox (sync), Nav2 (separate processes, own
  lifecycle managers), `frontier_tad_node` (`scoring_mode tad`, `selection_mode dfs`, blacklist
  0.5 m / 300 s, `min_pocket_area` 1 m²), `explore_coordinator` (timeout max(60 s, 15 s/m ×
  straight-line distance)). Nav2 as in [[Navigation stack]]: MPPI, inflation 0.22 m / 12,
  BT `explore_nav_to_pose.xml` (BackUp first, path kept 4 s), progress timeout 15 s.
- **Environment (not code):** run without the discovery server (none was running;
  `unset ROS_DISCOVERY_SERVER FASTRTPS_DEFAULT_PROFILES_FILE`), `ROS_DOMAIN_ID=34`, discovery
  range LOCALHOST. VS Code's snap GTK variables cleared, because they crashed Gazebo GUI and RViz
  (a first attempt that crashed on start is not counted).
- **Start:** robot at (0, 0), yaw 0, in chamber A, all three runs.
- **Observer:** a passive node (subscribes only). Coverage = open floor of the generated world
  (84.4 m², split into chambers A–F and tunnels) that the SLAM map marks as known.
- **End rules (fixed before run 1):** exploration complete + no goal and no movement for 3 min;
  ≥75 % coverage + robot within 0.5 m and coverage gain <0.5 m² for 5 min (user's rule);
  no movement for 10 min; cap 45 min sim time.

## 2. Run 1

![[run1_trajectory.png]]

| Time | Robot | Event | Outcome |
|---|---|---|---|
| 00:00–00:35 | A | goal 1 rejected (Nav2 still starting), resent; goal (−1.64, 0.15) is behind the robot | reached in 30 s; heading aligned at 8.6 s, then swung back to 170° error |
| 00:35 | A | goal (−2.63, 1.30), west dead end | reached |
| 01:07–02:04 | west dead end (−2.7, 0.9) | goals into D (3.58, −4.25), (2.23, −3.45); Collision Ahead, backup, spin | both aborted, blacklisted |
| 02:04–06:47 | A→B | 4 goals in chamber B: (3.23, 3.45), (4.48, 4.25), (7.23, 2.80), (6.53, 3.50) | all 4 timed out; 85 s stationary at (3.61, 3.97); 660° spin in place at 05:58 |
| 06:47–09:35 | B→C→E | 4 goals | all reached; coverage 50 % at 07:50, 75 % at 09:05 |
| 09:35–13:11 | north of C / B–E tunnel | (9.93, 5.96), (9.13, 5.86), (8.38, 5.36) | all timed out; sustained spinning 12:57–14:20 |
| 13:11–17:35 | F | (13.88, −5.54) timed out; (15.82, −6.11), (16.07, −5.66) aborted (Collision Ahead) | stuck at F entrance (13.7, −4.4) for 39 s + 31 s |
| 17:35–19:38 | D, D dead-end tunnel | 3 goals | all reached, incl. tunnel end (0.82, −6.59); 90 % at 18:35 |
| 19:38–23:14 | D tunnel → | goal (8.42, 5.40), 14 m away | timed out; robot spun in the tunnel 20:06–23:10 (≈3 turns clockwise, ≈3.4 counter-clockwise) |
| 23:14–45:07 | C↔F↔north of C | only 2 frontiers left: F end and (8.42, 5.37); alternate blacklist → expiry → retry | (8.42, 5.37) reached at 35:32 on its 4th attempt; F end never |
| 26:26 onward | | "exploration complete" printed whenever both were blacklisted (4 spells, 36–58 messages each) | |
| 45:07 | F entrance (13.6, −4.5), stationary 183 s | | **cap reached, coverage 98.5 %** |

## 3. Run 2

![[run2_trajectory.png]]

| Time | Robot | Event | Outcome |
|---|---|---|---|
| 00:00–00:42 | A | first goal (−1.56, 0.30) behind the robot | reached; yaw travelled 1069° in the first 45 s |
| 00:44–02:41 | A→D→C | **went south first** (run 1 and 3 went to B) | D reached at 01:08; (7.42, −3.34) timed out |
| 02:41–09:05 | C→B→E | 10 goals, 7 reached | 50 % at 03:11, 75 % at 06:53, 90 % at 09:38 |
| 09:44–15:20 | F | 4 goals: (13.37, −4.69) and (14.07, −6.04) timed out, F end aborted ×2 | 82 s stationary at F entrance (13.57, −4.74); 1167° spin in place at 12:45 |
| 15:20–18:11 | → D tunnel | (2.52, −6.49) | timed out |
| 18:11–21:11 | → west dead end | (−2.88, 1.71), 12 m | reached |
| 21:11–26:17 | A→…→D | F end (15.83, −6.25), 20 m | timed out after 304 s; ≈20 turns of commanded spinning 21:30–25:00 while crossing A |
| 26:17–29:22 | D dead-end tunnel | (2.51, −6.50), (1.96, −6.63), (0.71, −6.59) | all timed out (Collision Ahead, backup failed) |
| 29:24 onward | D tunnel (2.7, −6.6) | "exploration complete" ×37, then F end retried at 31:15 (timed out), tunnel end at 34:36 (timed out) | |
| 36:09–39:18 | D tunnel (2.88, −6.51), stationary | "exploration complete" ×64 | **end rule "complete + idle 3 min", coverage 98.0 %**. The tunnel-end blacklist would have expired at ~41:08, so exploration would most likely have resumed |

## 4. Run 3

![[run3_trajectory.png]]

| Time | Robot | Event | Outcome |
|---|---|---|---|
| 00:00–00:37 | A | first goal (−1.79, 0.20) behind the robot | reached; aligned at 11.3 s, then swung back to 144° error |
| 00:38–03:02 | A→B | 3 goals in B | all reached (run 1: all 4 B goals timed out) |
| 03:02–06:56 | B→C→F | (8.27, 1.20), (9.92, −1.30) timed out; F entrance (13.02, −4.25) reached; (13.87, −5.61) timed out | |
| 06:56–07:56 | F | F end (15.82, −5.11) | aborted (Collision Ahead) |
| 07:56–10:23 | D, D tunnel | 2 goals reached | 50 % at 04:29, 75 % at 09:26 |
| 10:23–11:26 | D tunnel (2.94, −6.54) | tunnel end (0.82, −6.61) | timed out; robot hardly moved (mean v 0.01 m/s) |
| 11:26–17:50 | → E, north of C | 4 goals, 3 reached; (10.77, 5.79) timed out | 90 % at 14:23 |
| 16:50–45:13 | C↔F↔A↔D | 3 frontiers left: F end, tunnel end, west dead end (−2.94, 2.1); each attempted 2–4 times | none reached; west dead end timed out ×3 (reached in runs 1 and 2) |
| 34:17, 37:59 | | "exploration complete" spells (×10, ×26) | |
| 45:13 | driving towards F end | | **cap reached, coverage 98.3 %** |

## 5. Quantitative results

| | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| End | cap 45 min | complete + idle 3 min (39:18) | cap 45 min |
| Final coverage | 98.5 % (83.1 m²) | 98.0 % (82.7 m²) | 98.3 % (83.0 m²) |
| 50 / 75 / 90 % at | 07:50 / 09:05 / 18:35 | 03:11 / 06:53 / 09:38 | 04:29 / 09:26 / 14:23 |
| Chamber F covered | 86 % | 81 % | 91 % |
| Path length | 129.6 m | 111.8 m | 177.5 m |
| Goals sent / reached | 28 / 10 | 27 / 11 | 25 / 10 |
| Timed out / aborted / rejected | 13 / 4 / 1 | 13 / 2 / 1 | 11 / 2 / 1 (+1 open) |
| "Failed to make progress" | 39 | 43 | 39 |
| BackUp / Spin / Wait recoveries | 18 / 14 / 7 | 15 / 8 / 2 | 16 / 8 / 3 |
| "Collision Ahead" (backup blocked) | 14 | 9 | 7 |
| Planner failure messages | 62 | 26 | 39 |
| Controller loop rate missed | 26 | 23 | 21 |
| Rotate in place (≥3 s, \|w\|>0.2, \|v\|<0.05) | 250 s | 180 s | 104 s |
| 30 s windows with >360° yaw change | 30 (~15 min) | 22 (~11 min) | 22 (~11 min) |
| Reversing (share of cmds with v < 0) | 18.5 % | 17.8 % | 15.9 % |
| Mean \|v\| while moving (limit 0.2) | 0.089 m/s | 0.084 m/s | 0.094 m/s |
| Reached goals: travelled / straight | median 1.02 | 0.99 | 1.10 |

## 6. Exploration behaviour

- All chambers A–E reached ≥96 % in every run. The only region never completed: the **far end
  of chamber F** (81–91 %).
- **Route order differed from the 2nd decision on:** the first frontiers chosen after the start
  were (0.86, −1.20), (1.94, 1.85) and (1.83, −2.55), from 4, 5 and 3 candidates. Run 2 went A→D
  first; runs 1 and 3 went A→B.
- **Revisits:** every blacklisted frontier that remained was retried after its 300 s expired.
  Lifecycle of the hard ones:

| Frontier | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| F far end ~(15.8, −6.1) | 5 attempts, never | 4 attempts, never | 5 attempts, never |
| D tunnel end ~(0.8, −6.6) | reached 1st try (19:20) | 4 attempts, never | 2 attempts, never |
| West dead end ~(−2.9, 1.9) | reached (00:35) | reached (18:11) | 3 attempts, never |
| North of C ~(8.4–9.9, 5.4–6.0) | 5 failures, reached 35:32 | reached 1st try | 1 failure, then reached |
| Chamber B goals | 4 of 4 timed out | 2 timeouts, then reached | all reached |

## 7. Navigation behaviour

- **Startup turn (3/3):** the first goal is always ~170–180° behind the robot. Heading aligns
  after 8.6 / 9.6 / 11.3 s, but within the next ~12 s the error returns to 170 / 178 / 144°. Yaw
  travel in the first 45 s: 581°, 1069°, 487°.
- **Sustained commanded spinning (3/3):** for minutes at a time the controller commands a steady
  ~0.45 rad/s in one direction while creeping forward (≈0.03 m/s), e.g. run 2 21:30–25:00. Checked
  against `/cmd_vel`: commanded and measured rotation agree in sign and shape, so it is commanded.
- **Turn rate ratio (3/3):** measured yaw change (map → base_footprint, SLAM-corrected) is
  **1.32×** the integrated commanded `w` in every window sampled (5 windows, 3 runs).
- **Speed:** never above 0.19 m/s (limit 0.2); mean 0.08–0.09 m/s while moving; ~17 % of
  commands are reversing.
- **Timeouts cut short goals that were still progressing:** in 28 of 37 timeouts the robot had
  closed ≥1 m on the goal in the last 60 s; many ended 1–2 m from the goal.
- **Straight segments:** reached goals were near-straight (median ratio 0.99–1.10). The local
  (MPPI) trajectory was not recorded, so local vs global path can't be compared yet.

## 8. Costmap behaviour

- **F entrance** (~13.8, −4.5): the free channel between the wall and two rock blobs is 1–2 cells
  (5–10 cm) wide in the global costmap; every plan into F threads through it. Boulder 7 sits at
  (14.09, −4.69).
  ![[F_end.png]]
- **D dead-end tunnel:** a 1–3-cell free channel that narrows to nothing near x ≈ 0.7.
  ![[D_tunnel.png]]
- Global costmaps at the same place look alike across runs (e.g. the D tunnel end in runs 1 and
  3), so these spots aren't explained by costmap differences alone.
- Not observed: stale obstacles or global/local disagreement. These weren't checked
  systematically (§16).

## 9. Stuck / failure cases

| Place | What happens | Runs |
|---|---|---|
| F entrance (13.6, −4.5) | stationary 30–180 s; Collision Ahead blocks backup; spins in place | 3/3 |
| D dead-end tunnel (1.3–2.9, −6.6) | stationary up to 195 s; multi-turn spins; Collision Ahead | 3/3 (failed at least once in each) |
| Chamber B, early (3.6, 4.0) | 85 s stationary, 660° spin | 1/3 (run 1) |
| E/B tunnel (12.5, 5.4) | 31–45 s stationary | 2/3 |
| Early goals from the west dead end into D | aborted, Collision Ahead | 1/3 (run 1) |

**D tunnel end, heading at the attempt:**

| Attempt | Heading at start (tunnel axis ≈180°) | Result |
|---|---|---|
| Run 1 goal 22 | 180° | drove in, reached |
| Run 3 goal 13 | 143° | mean v 0.01 m/s, timed out |
| Run 2 goal 24 | −128° | timed out |
| Run 2 goal 25 | −130° | timed out |

![[D_end_compare.png]]

## 10. End-of-exploration behaviour

No run ended by itself. In every run the last 1–3 frontiers were unreachable (F end; plus
the D tunnel end or the west dead end in runs 2–3). The system then cycles: attempt → timeout or
abort → blacklist 300 s → "exploration complete" printed every 3 s while everything is blacklisted
→ blacklist expires → same frontier sent again. Nothing listens to `/exploration_complete`, and
nothing marks a frontier permanently unreachable. Run 2's end (complete + idle) happened inside one
of these pauses, not at a true finish.

## 11. Cross-run comparison

| Event / location | Run 1 | Run 2 | Run 3 | Difference | Evidence |
|---|---|---|---|---|---|
| Startup turn overshoot | yes (170°) | yes (178°) | yes (144°) | magnitude only | pose + cmd |
| First route | A→B | A→D | A→B | candidate sets differed from the 2nd choice | frontier logs |
| Chamber B early | 4/4 timeouts | 1 timeout, then reached | all reached | different approach (from the west dead end vs from A) | goals table |
| F far end | never | never | never | none | 14 attempts in total |
| D tunnel end | reached | never | never | heading at entry (180° vs 37–50° off) | §9 |
| West dead end | reached | reached | never | run 3 tried only from far away, late (≥17 m) | goals table |
| End | cap (loop) | idle inside loop | cap (loop) | none in mechanism | blacklist logs |
| Sustained spinning | ~15 min | ~11 min | ~11 min | amount only | yaw windows |

## 12. Reproducibility

| Issue | Class |
|---|---|
| Startup turn overshoot | **A. Reproducible** |
| Sustained one-direction commanded spinning | **A. Reproducible** |
| Measured rotation 1.32× commanded | **A. Reproducible** |
| F far end never reached | **A. Reproducible** |
| Exploration never terminates (retry loop) | **A. Reproducible** |
| Timeouts on still-progressing goals | **A. Reproducible** (28/37) |
| D tunnel end failure | **C. Conditional**, associated with entry heading (n = 4) |
| West dead end failure | **C. Conditional**, possibly approach distance/order (n = 5) |
| Chamber B early failures | **D. Variable** |
| Route order differs from the start | **D. Variable**, path-dependent (map seen during the startup turn) |
| Planner "failed to create a plan from potential" | **E. Unknown** (62 / 26 / 39; consequence not traced) |

## 13. Abnormal behaviour database

| ID | Problem | Runs | Location | Freq | Evidence | Class |
|---|---|---|---|---|---|---|
| P01 | Overshoot on the startup turn to a goal behind the robot | 1,2,3 | A, start | 3/3 | pose, cmd | A |
| P02 | Sustained one-direction spinning while creeping forward | 1,2,3 | everywhere, mostly long goals | 3/3 | yaw windows, cmd | A |
| P03 | Measured turn rate 1.32× commanded | 1,2,3 | — | 3/3 | yaw vs ∫w | A |
| P04 | F far end unreachable; Collision Ahead at the 5–10 cm channel | 1,2,3 | F entrance | 3/3 | costmap snapshots | A |
| P05 | No termination: blacklist/expiry retry loop | 1,2,3 | last frontiers | 3/3 | blacklist logs | A |
| P06 | Coordinator timeout cancels goals still in progress | 1,2,3 | long goals | 28/37 | pose at timeout | A |
| P07 | D dead-end tunnel: fails when entering off-axis | 2,3 (ok in 1) | D tunnel | 2/3 | heading table | C |
| P08 | West dead-end frontier unreachable late in the run | 3 | (−2.9, 1.9) | 1/3 | goals | C |
| P09 | Early chamber B goals all time out | 1 | B | 1/3 | goals | D |
| P10 | Route diverges between identical runs | 1,2,3 | start | 3/3 differ | frontier logs | D |
| P11 | Backup recovery blocked ("Collision Ahead") | 1,2,3 | narrow places | 14/9/7 | behaviour logs | A |
| P12 | Planner potential-path failures | 1,2,3 | various | 62/26/39 | planner logs | E |
| P13 | Controller loop rate missed | 1,2,3 | — | 26/23/21 | controller logs | E |

## 14. Potential research problems

- Controller-level rotation: overshoot and long one-direction spinning (P01–P03).
- Narrow passages and dead ends for a skid-steer robot that can enter but not turn (P04, P07, P11).
- Exploration termination and handling of unreachable frontiers (P05, P08).
- Goal timeout / progress estimation for long goals (P06).
- Run-to-run variability from the initial map state (P10).

## 15. Research questions

- Why does the controller keep commanding rotation after alignment, and does the 1.32× turn-rate
  mismatch between command and response explain it (P01–P03)?
- Can frontier selection or goal placement account for whether the robot can turn in a
  passage, not only whether its footprint fits (P04, P07)?
- What termination rule distinguishes "explored" from "remaining frontiers unreachable", and
  how should a repeatedly failing frontier be retired (P05)?
- Would a progress-based timeout (distance closed over time) instead of a straight-line budget
  cut fewer still-progressing goals (P06)?
- How much of the route variability comes from the startup turn (P10)?

## 16. Evidence still needed

- MPPI's chosen trajectory and critic costs during spinning episodes (not recorded).
- `/odom` (EKF) yaw vs map yaw vs Gazebo ground-truth pose, to separate actual over-rotation
  from estimation (P03).
- `/cmd_vel_nav` vs `/cmd_vel` (velocity smoother, collision monitor) during P02.
- Frontier candidate lists and scores at each decision (only the chosen one is logged).
- More D-tunnel attempts to confirm the heading dependence (n = 4).
- CPU load against the missed controller rates (P13).

## 17. Things not to change yet

- Inflation and footprint: the narrow spots have similar costmaps across runs, and P07 points
  at heading, not width.
- EKF rate: P03 (the 1.32× ratio) is the same at 10 and 30 Hz, so it is not caused by the EKF rate.
  The startup spin (P01) **is** much worse at 10 Hz; see the follow-up below.

## Follow-up 2026-10-09: EKF 10 Hz vs 30 Hz, startup turn only

6 GUI launches, alternating, otherwise identical; stopped when the first goal was reached. The
30 Hz runs used a temporary edit of the *installed* `ekf.yaml`, restored afterwards. Data:
`~/baseline_runs_2026-10-08/ekf_ab_2026-10-09/`.

| Run | EKF | Aligned at | Max error after aligning | Total turning | Time to goal |
|---|---|---|---|---|---|
| t1 | 10 Hz | 8.1 s | 180° | 1406° (~4 turns) | 43.8 s |
| t3 | 10 Hz | 8.4 s | 180° | 1429° (~4 turns) | 42.9 s |
| t5 | 10 Hz | 12.4 s | 62° | 344° | 34.0 s |
| t2 | 30 Hz | 7.3 s | 10° | 167° | 15.1 s |
| t4 | 30 Hz | 7.4 s | 76° | 358° | 58.7 s |
| t6 | 30 Hz | 7.2 s | 78° | 407° | 34.8 s |

- 10 Hz: mean overshoot 140°, mean turning 1059°. Multi-turn spinning in 2 of 3 runs.
- 30 Hz: mean overshoot 55°, mean turning 311°. No multi-turn spin. Overshoot of ~77° still in 2 of 3.
- Measured/commanded turn ratio 1.26–1.33 at both rates.
- 2026-10-15, EKF back at 30 Hz in the source ([[Relay rates]]), same conditions, 3 runs: overshoot
  12°, 87°, 65° (mean 55°), mean turning 319°, no multi-turn spin, 3/3 reached the goal in 34–37 s.
  Same as the 30 Hz runs above. The ~65–87° overshoot on goals behind the robot is still open.
- n = 3 per rate: a strong difference, small sample.
- Two earlier launches (both 10 Hz) hit the startup lifecycle hang ([[Nav2 not loaded]]) without a
  discovery server, and one was ended by Gazebo exiting. They are excluded and were re-run.
- Blacklist duration: the loop (P05) is structural; a different duration only changes its period.
- MPPI critics, until the MPPI trajectory data (§16) is recorded.
