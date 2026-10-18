---
tags: [issue]
---
# Run to 90 percent 2026-10-18

The same three setups as [[Tunnel tracking 2026-10-18]] (NavFn / + path smoothing / + smoothing +
MPPI tuning), but each run goes on until the cave is explored rather than stopping at 10 min.
GUI runs, 2 per setup, interleaved. Branch `exp/tunnel-tracking`. Interim: the stop rule needs a
decision (below).

## Stop rules (the user's, fixed before the runs)
A run ends at the first of:
1. **coverage ≥ 90 %** of the true cave floor, `reached_90`
2. **< 0.5 m² of coverage gained in 3 min**: stuck at an unreachable spot, `stuck`
3. 45 min of sim time, `cap` (safety only, never hit)

Coverage is the true open-floor cells (generator `field.npz`, 84.4 m², from
`~/baseline_runs_2026-10-08/`) that the SLAM map marks as known. It is the same measure as
[[Baseline runs 2026-10-08]]. Scripts, data and figures are in `assets/run90_2026-10-18/`.

## Results
| Run | Stop | Ended at | Coverage | Stuck where |
|---|---|---|---|---|
| base_1 | stuck | 5.2 min | 28.5 % | (2.4, −6.6), end of the D-side dead-end tunnel |
| base_2 | **90 %** | **10.8 min** | 90.0 % | — |
| smooth_1 | stuck | 10.5 min | 71.2 % | (13.6, −4.3), on the way to F |
| smooth_2 | **90 %** | **18.0 min** | 90.3 % | — |
| tuned_1 | stuck | 4.2 min | 17.1 % | (−2.8, 1.3), west dead end |
| tuned_2 | stuck | 6.9 min | 31.4 % | (2.4, −6.7), end of the D-side dead-end tunnel |

In every `stuck` stop, the robot spent the last 3 min inside a 1.2–1.8 m box, with 8–9 "Failed
to make progress", BackUps and "Collision Ahead". These are the dead-end traps P07, P08 and P04
from [[Baseline runs 2026-10-08]]: the robot drives to the end of a narrow dead end and can't
turn round.

![[run90_coverage.png]]
![[run90_traj_tuned_2.png]]
*`tuned_2`: straight down the D-side dead-end tunnel to the frontier at its end (goal 5), then
stuck turning round (BackUp, Spin).*

![[run90_traj_base_2.png]]
*`base_2`, the fastest run to 90 %: 10.8 min.*

![[run90_traj_smooth_2.png]]
![[run90_traj_base_1.png]]
![[run90_traj_smooth_1.png]]
![[run90_traj_tuned_1.png]]
![[run90_metrics.png]]

### Tunnel tracking, travelling part only
The stuck minutes (pivoting while wedged) would count as tunnel driving, so each run's final
180 s is left out. Pooled with the four 10-min runs of [[Tunnel tracking 2026-10-18]], that
gives 4 runs per setup:

| In tunnels | base | smooth | tuned |
|---|---|---|---|
| Heading deviation, median | 6.8° | 6.7° | **3.4°** |
| Heading deviation, p90 | 31.7° | 32.2° | **14.2°** |
| … p90 per run | 17 / 36 / 39 / 35 | 31 / 41 / 16 / 41 | **9 / 18 / 12 / 17** |
| Turn reversals per m | 0.84 | 0.98 | **0.42** |

The tuned runs in this round drove only 2 m and 7 m of tunnel before getting trapped, so they
add little weight.

## Reading
- **Tracking: tuned is better in 4 runs out of 4.** It halves the heading deviation and the turn
  reversals. That replicates [[Tunnel tracking 2026-10-18]].
- **Finishing the cave is decided by dead ends, not by tracking.** 4 of the 6 runs were trapped at
  the end of a dead-end tunnel within 4–11 min. Only base_2 and smooth_2 reached 90 %.
- **Tuned was trapped in both runs, and early** (17 %, 31 %). One possible reason is that lower
  angular sampling noise (`wz_std` 0.2) gives MPPI fewer turn-round candidates in a tight dead end.
  That is a hypothesis; n = 2.
- Under the 3-min rule, an early trap ends the run. Under the baseline's rule (stuck counts only
  above 75 % coverage), the blacklist would have freed the robot after 5 min and the run would have
  gone on.

## Open
- **Stop rule:** should "stuck for 3 min" apply only after most of the cave is covered (the
  baseline used ≥ 75 %)? This needs the user's decision before a re-run.
- **Dead-end turn-round:** this is the real blocker for finishing the cave in every setup.
  Candidates: detect a dead end before entering (frontier inside a corridor narrower than the
  0.39 m pivot diameter plus margin), or reverse out along the path instead of turning.
