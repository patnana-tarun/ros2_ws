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

## Configuration
`config/nav2_params.yaml` holds the Nav2 and SLAM Toolbox parameters for this robot. It
replaces TurtleBot3's `burger.yaml`, and its choices are explained in [[Navigation stack]].

## Other folders
`comparison/`, `validation/` and `kinematic_sim/` are the earlier offline studies (TAD vs.
other frontier policies, and checks that the implementation matches the paper). They don't
depend on ROS and were not changed in the port. Some of their comments still mention
TurtleBot3.
