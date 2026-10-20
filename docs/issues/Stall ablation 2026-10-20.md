---
tags: [issue]
---
# Stall ablation 2026-10-20

Which of the demo fixes in [[Navigation fixes 2026-10-19]] causes the stuck regression (stuck
time 7 % → 33 %, goal success 59 % → 39 %)? The version under test is kept as tag `nav-demo-v2`
(branch `exp/tunnel-tracking`). The ablation is on branch `exp/stuck-ablation`. Raw data:
`~/ablation_runs_2026-10-20/`; the demo-v2 runs are in `docs/demo_runs_2026-10-19/` (moved there
from `~/demo_runs_2026-10-19/`). Chart, numbers and scripts: `assets/ablation_2026-10-20/`.

## Method
Four variants, each = demo v2 with **one** change undone. 3 GUI runs each, interleaved A, B, C, D
× 3, same protocol as [[Full comparison 2026-10-19]] (90 % coverage, stuck above 75 %, 40 min cap,
30 s give-up in all). Compared with demo v2 (3 runs) and the "before" tuned setup (3 runs).

| Variant | Undoes | How |
|---|---|---|
| A | planning only through explored space | `config/nav2_params_abl_unknown.yaml`: `allow_unknown: true`, global costmap on `/map` |
| B | goal hand-over at 0.5 m | `config/nav2_params_abl_handover.yaml`: `GoalCritic` / `PathFollowCritic` back to 1.0 m |
| C | sim track width 0.34 m | `skid_track:=0.43`, a new launch argument (checked: the sim then loads `wheel_separation` 0.43) |
| D | planner pre-check | `precheck_path:=false` |

## Results
Mean, with per-run values in brackets.

| | before (tuned) | demo v2 | A | B | C (0.43) | D |
|---|---|---|---|---|---|---|
| Time stuck | **7 %** (12/3/8) | 33 % (22/30/49) | 32 % (28/21/48) | 30 % (19/31/40) | 21 % (30/14/18) | 43 % (45/42/42) |
| Goal success | **59 %** | 39 % | 39 % | 40 % | 43 % | 24 % |
| Largest MPPI turn command | 0.62 | 0.19 | 0.22 | 0.34 | **0.62** | 0.60* |
| Start-up turning (goal behind) | 214° | 41° | 37° | 43° | **142°** | 39° |
| Spins (≥ 300° in 60 s, per run) | 2.7 | **0** | **0** | **0** | 3.3 | 0.3 |
| Large open-area deviations | 7.1 % | 3.2 % | 1.1 % | 2.0 % | 7.6 % | 1.7 % |
| Reached 90 % | 2 of 3 | 2 of 3 | 2 of 3 | 1 of 3 | 2 of 3 | 0 of 3 |

\* In D the 0.60 rad/s comes from Spin recoveries (2.9 per 10 min), not from MPPI.

![[ablation.png]]

## Reading
- **The 0.34 m sim track width causes both the gain and the hesitation.** With 0.34, every
  variant has no spins (or 0.3 per run), start-up turns of about 40°, and 1–3 % large open-area
  deviations. Undoing only the track width (C) brings back the spins (3.3 per run), long start-up
  turns (142°), 8 % deviations and full-size MPPI turn commands. The steady in-place turn rate
  is the same at 0.43 and 0.34 (step test in [[Navigation fixes 2026-10-19]]), so the effect has
  to be in the transient response: a narrower DiffDrive track gives a smaller wheel-speed
  difference per command. Not yet measured directly.
- **No single change explains the stalls.** All 15 runs with the demo fixes stalled more than
  all 3 "before" runs: 14–49 % against 3–12 %, Mann-Whitney p = 0.002. Undoing the track width
  helps most (21 %). Undoing the pre-check makes it worse (43 %), so the pre-check helps. Undoing
  the unknown-space policy or the hand-over changes nothing measurable.
- **Ruled out as causes of the stalls:** the world (the generated `cave.sdf` is byte-identical
  to the committed one, unchanged since 2026-10-06), and timing (RTF 1.000 and 13–14.5
  controller commands/s in every run).

## Open
- Is "before" still 3–12 % stuck when rerun today? It was run on 2026-10-19 with the code of that
  time. If it reproduces, the remaining stall excess at 0.43 (C: 21 %) comes from a combination of
  the planner changes, and needs undoing pairs at 0.43.
- Can path accuracy be kept without the hesitation? For example a track width between 0.34 and
  0.43, or limiting the robot's turn acceleration in the velocity smoother instead, so the
  damping is explicit in the configuration rather than hidden in the sim model.
