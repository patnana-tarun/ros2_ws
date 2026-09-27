# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A ROS 2 Jazzy colcon workspace for the explorer robot. It relays SLAM output (`/map`, `/tf`)
over a lossy BATMAN-adv mesh, holds the robot's URDF/Gazebo model, and explores autonomously
(frontier/TAD + Nav2). This is the sender side only. The receiver is external.

| Package                    | Type         | Contents |
|----------------------------|--------------|----------|
| `src/my_mesh_interfaces`   | ament_cmake  | `MeshMap`, `MeshTf`, `MeshScan`, `SenderStatus` |
| `src/mesh_nodes`           | ament_python | `explorer_relay_node` (exe `explorer_relay`), launch + YAML |
| `src/explorer_description` | ament_cmake  | URDF/xacro, Gazebo Harmonic launch, cave world generator, wheel+IMU EKF config |
| `src/explorer_exploration` | ament_python | frontier/TAD exploration nodes, Nav2 + SLAM Toolbox params, bringup launch |
| `src/explorer_bringup`     | ament_python | real robot on the Pi: TB6612FNG/encoder and MPU-9250 drivers, robot launch |

## Commands

```bash
colcon build && source install/setup.bash
ros2 launch mesh_nodes explorer_relay.launch.py            # use_sim_time:=true with Gazebo
ros2 launch explorer_description explorer_gazebo.launch.py rviz:=true
ros2 launch explorer_exploration bringup.launch.py                 # world:=cave.sdf by default
ros2 launch explorer_exploration benchmark_headless.launch.py      # headless + metrics
ros2 run explorer_exploration manual_drive                         # manual override (pauses exploration)
ros2 launch explorer_exploration bringup.launch.py sim:=false rviz:=false   # real robot, on the Pi
```

There is no test suite or linter. The xacro include uses `$(find explorer_description)`, so
source the workspace before running `xacro` or `check_urdf`.

## Documentation: `docs/` is an Obsidian vault and the single source of truth

Design rationale lives in the vault, not here: QoS, the envelope, the throttle, PDR, robot
dimensions and limitations. Start at `docs/Home.md`. Before changing relay behaviour, read
`docs/concepts/` (especially `QoS design.md` and `Map-in-flight throttle.md`). The receiver's
QoS must stay compatible with the relay's.

Rules for updating docs (the user asked for this to happen automatically, without asking):
- One note per idea, and each fact lives in exactly one note. Other notes link with
  `[[Note name]]` instead of repeating it.
- Frontmatter `tags:` is one of `moc`, `package`, `concept`, `robot`, `issue`, `external`, `log`.
- Topics are listed only in `concepts/Topics.md`. Limitations are listed only in
  `Known limitations.md`.
- Every session that changes something appends to `log/YYYY-MM-DD.md` with the sections
  Done / Verified / Not yet verified / Found, and links it from `Home.md`.
- Keep notes short, but don't drop information. The user builds their project report from
  these notes.
