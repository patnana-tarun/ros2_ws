---
name: rover-tune
description: Self-correcting tuning loop for the explorer rover in Gazebo + RViz using the `rover` MCP server (tools/rover_mcp). Use when running, watching, debugging or tuning navigation/exploration in simulation, when the user reports the robot spinning, stalling, leaving the path or not starting, or when comparing configurations.
---

# Rover tuning loop

The `rover` MCP server (tools `mcp__rover__*`, code in `tools/rover_mcp/`, design in
`docs/concepts/Tuning loop.md`) runs the sim in an isolated env (ROS domain 90, localhost,
GZ partition `rover_mcp`, snap-free GUI env), watches it, and measures with the same definitions
as the report (`validate.py`). If the tools are not loaded, run the same calls from a shell:
`tools/rover_mcp/.venv/bin/python tools/rover_mcp/mcp_call.py 'tool {"arg":1}' ...`.

## Loop
1. `preflight` - fix every listed problem first (stale processes, unbuilt src edits, snap env).
2. Baseline: `smoke_test` on the current config. FAIL -> diagnose before anything else.
3. `sim_start`, then `observe(seconds=120)`. It returns early with a map and a Gazebo screenshot
   when an alert fires. Read the metrics, not just the picture.
4. Diagnose: `logs(source="goals")`, `logs(level="WARN")`, `map_view(radius=4)`,
   `screenshot_series`, `ros2 "param get ..."`, `ros2 "topic hz ..."`. Write the hypothesis with
   `journal_note` BEFORE changing anything. When a still does not show the behaviour (oscillation,
   U-turn, wedge, creeping), make `map_gif(seconds=60)` (track growing on the map) or
   `record_gif("gazebo")` (call `gz_camera("follow")` first, or the robot is a few pixels): the GIF is for the user and the docs, the returned frame sheet is for you.
5. Change ONE thing. Quick probe: `set_params` (live, journaled). Keeper: edit the YAML in `src/`,
   `build`, then `smoke_test` (a launch that no longer spawns the robot must never reach step 6).
6. Confirm with `experiment_start` (n >= 2 per arm, GUI, interleaved, same stop rules), then
   `experiment_status` / `compare` (pool with an older baseline folder if useful).
7. Record: docs log + issue note (Done / Verified / Not yet verified / Found), Comparisons.md only
   for confirmed A/Bs, commit on the exp branch, push.

## Rules (from the user)
- Path accuracy first: xte, heading deviation, large-deviation %, rotation events, plans through
  unknown rank above speed or coverage time.
- GUI runs, not headless, for anything reported. One `observe` window is a hint, never a result.
- Experiments on an `exp/*` branch; `feat/demo` and `main` stay clean. Reverse only in tunnels.
- Do not touch the USB tether setup (known source of gz multicast "No such device").
- Never pause Gazebo during a run you need: > ~4 s kills Nav2 (lifecycle bond on wall time).
- Read the memory note `nav-lessons` before analysing: retrace windows are excluded from tracking
  metrics, `stuck_after_most` is not "wedged", report per-run ranges, not one mean.
- `build/`, `install/`, `log/`, `__pycache__/`, `tools/rover_mcp/runs/` (since 2026-10-21) and
  `data/` (raw run data, since 2026-10-25) are git-ignored; never force-add them.

## Alert -> first suspects
| Alert / symptom | Check first | Note |
|---|---|---|
| `launch_exited` + "symbol lookup error ... libpthread" | snap GTK vars leaked into the env | GUI crashes in VS Code terminal |
| `no_pose` / `no_map`, empty Gazebo | discovery-server env leaking in (preflight `ros_isolation`), spawn | Discovery server not running |
| `not_moving`, coordinator "waiting for Nav2" | `ros2 "action info /navigate_to_pose"` (0 servers?), lifecycle | Nav2 not loaded |
| `low_rate` /cmd_vel_nav ~7 Hz | MPPI too heavy for 15 Hz (batch size, horizon), CPU load, `low_rtf` | Path tracking and stalls 2026-10-18 |
| `rotation` at the start or in tunnels | over-rotation (sim yaw rate 1.2-1.3x), `skid_track`, MPPI swinging past the path | Navigation fixes 2026-10-19, Stall ablation 2026-10-20 |
| stalls / wedges in tight passages | planner `robot_radius` (0.22), reverse controller, retrace guard | Tunnel-reverse 2026-10-20 |
| robot stands still with a valid path, also in open space | path 45-55 deg off the heading: MPPI finds no good rollout; check `hdev` at the stall | nav-lessons memory, Known limitations #26 |
| slow run | `time_budget_pct`: standing still was 40-54 %, U-turns only 2-4 % (tunnel-reverse) | nav-lessons memory |
| `follow_path` "Aborting handle" every ~4.6 s | BT restarts FollowPath on every smoothed path; tracking errors cluster in the first cycle after an abort | Path tracking and stalls 2026-10-18; seen live 2026-10-20 |
| `plans.with_unknown_cells` > 0 | `precheck_path`, `allow_unknown`, explored map | Navigation fixes 2026-10-19 |
| `low_rtf` | other sims running (preflight), GPU offload (`gpu_processes` empty?) | |
| `coverage_stalled` above 75 % | unreachable frontier, blacklist timing (`stall_timeout`) | Run to 90 percent 2026-10-18 |
