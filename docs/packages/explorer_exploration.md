---
tags: [package]
path: src/explorer_exploration
build_type: ament_python
---
# explorer_exploration

Autonomous exploration: it picks the next frontier with the TAD score
([[Frontier exploration]]) and sends it to Nav2. It was written for TurtleBot3 on ROS 2 Humble
and ported to this robot on Jazzy on 2026-09-26 ([[2026-09-26]]).

## Nodes
| Executable            | Role |
|-----------------------|------|
| `frontier_tad_node`   | `/map` → frontier clusters → TAD score → `/best_goal`, plus `/frontier_markers` for RViz and `/exploration_complete` |
| `explore_coordinator` | sends `/best_goal` to Nav2's `navigate_to_pose`, one goal at a time, and logs how each goal ended |
| `metrics_logger`      | exploration time, path length (from `/odom`), goal count and coverage, printed as one `METRICS_SUMMARY` line |
| `manual_drive`        | keyboard driving that pauses exploration while it runs (below) |
| `lifecycle_startup`   | sends STARTUP to the SLAM and Nav2 lifecycle managers `startup_delay` s (default 8) after launch, then exits ([[Nav2 not loaded]]) |
| `demo_chase_cam`, `demo_view_box`, `demo_recorder` | camera views and recorder for the backup demo video ([[Demo recording]]) |

Topics are in [[Topics]].

## Launch files
| File                           | Starts |
|--------------------------------|--------|
| `bringup.launch.py`            | sim ([[Gazebo simulation]], default world `cave.sdf`) + SLAM Toolbox + Nav2 + the two nodes + RViz |
| `benchmark_headless.launch.py` | the same with no Gazebo window or RViz, plus `metrics_logger` |
| `explore.launch.py`            | only the two nodes, with the TAD parameters as launch arguments |
| `sim_loop.launch.py`           | endless data for relay tests: `sim_loop` restarts `tunnel_reverse.launch.py` fresh each time true-floor coverage reaches `target_pct` (85 %), plus one `explorer_relay_node` for the whole session; until Ctrl-C |
| `demo_record.launch.py`        | `tunnel_reverse.launch.py` + chase camera + box-following RViz + side-by-side MP4 ([[Demo recording]]) |

```bash
ros2 launch explorer_exploration bringup.launch.py                        # watch it explore the cave
ros2 launch explorer_exploration bringup.launch.py world:=cave_open.sdf
ros2 launch explorer_exploration benchmark_headless.launch.py scoring_mode:=nearest
ros2 launch explorer_exploration sim_loop.launch.py sim_args:='rviz:=false'   # restart at 85 %, until Ctrl-C
```

`sim_loop` also restarts a run when the sim launch exits, no `/map` comes within 180 s,
`/exploration_complete` arrives below the target, or coverage gains < 0.5 m² in `stall_restart_s`
(300 s; 0 = never). Coverage uses the same true-floor measure as the [[Tuning loop]], from
`data/demo_runs_2026-10-19/field.npz`, which fits `cave.sdf` only. One row per run (wall-clock start,
end, coverage, reason) goes to `~/.ros/sim_loop_cycles.csv`. Use it to cut the restart gaps
(about 20 s without `/map` and `/tf`) out of the communication metrics. The relay keeps one
`session_id`, and its sequence numbers continue across restarts. It runs with `use_sim_time` false,
because the sim clock goes back to 0 on each restart and the relay's timers and stamps use wall time anyway.

Gazebo and RViz crash at start if launched from the VS Code terminal
([[GUI crashes in VS Code terminal]]).

## Manual override
```bash
ros2 run explorer_exploration manual_drive      # in a second terminal
```
- **While it runs:**
  - It sends a heartbeat on `/manual_override`.
  - `explore_coordinator` cancels the current Nav2 goal and sends no new ones.
  - The keys `w`/`x`/`a`/`d`/`s` set speed and turn, up to 0.2 m/s and 0.6 rad/s.
- **Closing it** (`q`, Ctrl+C, or closing the terminal) stops the robot, and exploration
  resumes by itself: immediately on `q` or Ctrl+C, or within 1 s when the heartbeat stops.
- **Safety:** commands go to `/cmd_vel_nav`, the same input Nav2's controller uses, so they
  still pass through the velocity smoother and the collision monitor. Without Nav2 running,
  add `--ros-args -p topic:=/cmd_vel`.

## Configuration
`config/nav2_params.yaml` holds the Nav2 and SLAM Toolbox parameters for this robot. It
replaces TurtleBot3's `burger.yaml`, and its choices are explained in [[Navigation stack]].

## Other folders
`comparison/`, `validation/` and `kinematic_sim/` are the earlier offline studies (TAD vs.
other frontier policies, and checks that the implementation matches the paper). They don't
depend on ROS and were not changed in the port. Some of their comments still mention
TurtleBot3.
