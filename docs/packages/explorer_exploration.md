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

Topics are in [[Topics]].

## Launch files
| File                           | Starts |
|--------------------------------|--------|
| `bringup.launch.py`            | sim ([[Gazebo simulation]], default world `cave.sdf`) + SLAM Toolbox + Nav2 + the two nodes + RViz |
| `benchmark_headless.launch.py` | the same with no Gazebo window or RViz, plus `metrics_logger` |
| `explore.launch.py`            | only the two nodes, with the TAD parameters as launch arguments |

```bash
ros2 launch explorer_exploration bringup.launch.py                        # watch it explore the cave
ros2 launch explorer_exploration bringup.launch.py world:=cave_open.sdf
ros2 launch explorer_exploration benchmark_headless.launch.py scoring_mode:=nearest
```

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
