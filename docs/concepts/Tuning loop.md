---
tags: [concept]
---
# Tuning loop

How a navigation change is tried, judged and confirmed in simulation, and the tool that runs it:
the `rover` MCP server in `tools/rover_mcp/` (branch `exp/rover-mcp`, added [[2026-10-20]]).
Claude calls it as tools; the same calls run from a shell with `mcp_call.py`.

## Why
Lessons from the sessions of 2026-09-26 … 2026-10-20 that this replaces:

| Problem in earlier sessions | Now |
|---|---|
| The user spotted spins, stalls, "no map", "not moving for 10 min" from screenshots | Health watchdog: `observe` stops early on an alert and attaches the map and a Gazebo screenshot |
| GUI launch worked only sometimes ([[GUI crashes in VS Code terminal]], [[Discovery server not running]]) | Every sim gets the isolated env (`simenv.sh`); `preflight` checks it |
| YAML edits did not take effect (no symlink install) | `preflight` lists `src/` files that differ from `install/`; `build` tool |
| A change broke the spawn and was only noticed later | `smoke_test` gate after every change |
| A new recorder + runner script copied per experiment; results spread over `~/…_runs_*` folders | One harness `experiment.py` driven by a YAML spec; all runs under `tools/rover_mcp/runs/` |
| `pkill -f` patterns killed their own shell (exit 144) | Processes found by `GZ_PARTITION` in their environment, never shells |
| 3 MB run JSONs too big to read | Compact `summary.json` per run, full 10 Hz track in `track.npz` |

## The loop
1. `preflight` → 2. `smoke_test` (baseline) → 3. `sim_start` + `observe` → 4. diagnose (`logs`,
`map_view`, `screenshot`, `ros2`, `gz`) and write the hypothesis (`journal_note`) → 5. change one
thing (`set_params` live, or YAML + `build`) → `smoke_test` → 6. `experiment_start` (n ≥ 2 per arm,
GUI) → `compare` → 7. docs + commit. One `observe` window is a hint; only step 6 confirms
(see [[Comparisons]]). The step-by-step version with the alert → suspect table is the project skill
`.claude/skills/rover-tune/SKILL.md`.

## Isolation
`simenv.sh`: ROS domain 90, discovery range LOCALHOST, no discovery server, GZ partition
`rover_mcp`, snap GTK variables removed, NVIDIA PRIME offload. Sim traffic never reaches the mesh
([[Mesh network setup]]). To watch a sim started by hand, source `simenv.sh` in that terminal first.

## Metrics
Same definitions as `docs/demo_runs_2026-10-19/validate.py`, computed live from 10 Hz samples:

| Metric | Definition |
|---|---|
| xte, heading deviation | distance / angle to the path the controller follows (`/plan_smoothed` if fresh, else `/plan`); reversing counts as on-track |
| tracking samples | driving forward (vx > 0.05) and not stuck |
| stuck | < 0.5 m net over the surrounding 60 s |
| tunnel / open | LiDAR left + right clearance < 1.2 m / > 2.0 m |
| large deviation | xte > 0.10 m or heading > 30° |
| rotation event | ≥ 300° of turning within 60 s while < 1 m net |
| stall episode | ≥ 3 s with a velocity command but no motion |
| time budget | forward / reverse / turn on the spot / creep / still (as `budget.py`) |
| coverage | true cave floor (`field.npz`) seen as known in `/map` |
| plans through unknown / lethal | share of `/plan` points on unknown or inscribed+ global-costmap cells |
| goal outcomes | `explore_coordinator` messages: sent, reached, gave_up, timeout, no_progress, no_path_blacklisted, retrace |

## Alerts
`not_moving` (< 0.3 m in 60 s), `rotation`, `node_died` / `launch_exited` (launch log),
`no_pose`, `no_map`, `no_clock` (sim time frozen), `low_rtf` (< 0.4), `low_rate` (scan < 4 Hz,
odom < 10 Hz, `/cmd_vel_nav` < 10 Hz while driving; expected 7 / 30 / 15 Hz), `coverage_stalled`
(< 0.5 m² in 180 s below 90 %), `complete`.

## Experiments
Stop rules of [[Full comparison 2026-10-19]]: start at the first `/plan`; stop at 90 % coverage,
≥ 75 % with < 0.5 m² gained in 180 s, the cap (40 min), exploration complete, or the launch dying.
Arms run interleaved. Each run writes `launch.log`, `summary.json`, `track.npz`, `trajectory.png`;
the experiment writes `comparison.md`, `comparison.png` and `comparison_trajectories.png`.

## Windows and pictures
Gazebo and RViz are native Qt/OpenGL windows, so browser tools (Playwright, Chrome DevTools)
cannot reach them. The server reads the window pixels through X11 (works while the window is
covered) and sends clicks, drags, wheel and keys through XTEST (raises the window and moves the real
mouse). Window aliases `gazebo` / `rviz` match the exact titles (`Gazebo Sim`, `… - RViz`). The
Gazebo camera is moved through its GUI services (`/gui/follow`, `/gui/move_to/pose`).

When a still can't show the behaviour, `map_gif` animates the track growing on the map and
`record_gif` records a window (follow the robot with `gz_camera` first, or it is a few pixels).
Example: tunnel-reverse backing out of a dead end (red), turning at the junction (orange), then
driving forward (green):

![[map_gif_tunnel_reverse_exit.gif]]

`observe` / `map_view` render (costmap: orange inflation, red lethal; blue `/plan`):

![[observe_map.png|500]]

## Do not pause the sim
Pausing Gazebo for more than ~4 s ends the run: Nav2's lifecycle bond runs on wall time, so
`lifecycle_manager_navigation` declares `collision_monitor` dead and shuts Nav2 down (seen
[[2026-10-20]]). `gz_world` refuses to pause unless forced.
