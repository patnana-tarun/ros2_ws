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

No symlink install: after editing YAML, launch or Python files in `src/`, rebuild, or the old
installed copy runs.

```bash
# Build
colcon build && source install/setup.bash
colcon build --packages-select explorer_exploration          # after nav/exploration edits only

# Simulation, explore the cave (Gazebo + RViz + SLAM + Nav2 + frontier exploration)
ros2 launch explorer_exploration tunnel_reverse.launch.py    # CURRENT best: reverse only in tunnels (exp/nav-speed)
ros2 launch explorer_exploration tunnel_reverse.launch.py rviz:=false
ros2 launch explorer_exploration bringup.launch.py           # plain defaults (world:=cave.sdf)
ros2 launch explorer_exploration reverse_out.launch.py       # older variant: backs out anywhere (rejected by the user)
ros2 launch explorer_exploration benchmark_headless.launch.py   # headless + metrics (reported results are GUI runs)
ros2 launch explorer_exploration tunnel_reverse.launch.py log_level:=controller_server:=debug  # e.g. rotation-shim debug
# tunnel_reverse.launch.py fixes heading_weight 1.0, explored_cancel true, unknown_margin 2 in its
# include: change them there (a command-line value does not override an include's argument)

# Simulation, robot model only (no exploration)
ros2 launch explorer_description explorer_gazebo.launch.py rviz:=true

# Manual driving (pauses exploration while it runs)
ros2 run explorer_exploration manual_drive

# Real robot, on the Pi
ros2 launch explorer_exploration bringup.launch.py sim:=false rviz:=false
ros2 launch explorer_bringup robot.launch.py mock:=true          # drivers only, no hardware

# Mesh relay (sender side; /map and /tf onto the BATMAN-adv mesh)
ros2 launch mesh_nodes explorer_relay.launch.py                  # on the robot
ros2 launch mesh_nodes explorer_relay.launch.py use_sim_time:=true   # with Gazebo
```

Sim runs for tuning and comparisons go through the `rover` MCP tools, not the launches above
(isolated env, metrics, run folders). From a shell when the tools are not loaded:

```bash
R=tools/rover_mcp; PY=$R/.venv/bin/python
$PY $R/mcp_call.py 'preflight {}'                                  # check env, stale sims, unbuilt edits
$PY $R/mcp_call.py 'smoke_test {}'                                 # 150 s pass/fail gate after a change
$PY $R/mcp_call.py 'sim_start {"args":"rviz:=false"}' 'observe {"seconds":120}' 'sim_stop {}'
$PY $R/mcp_call.py 'experiment_start {"spec":"name: ab\nn: 3\ncap_s: 1500\nstop: {target_pct: 95}\narms:\n  base: {launch: tunnel_reverse.launch.py, args: \"\"}\n  cand: {launch: tunnel_reverse.launch.py, args: \"\"}"}'
# an arm can run an older commit: build it in a worktree and add  overlay: <worktree>/install
#   git worktree add --detach /tmp/base <commit> && (cd /tmp/base && colcon build --packages-select explorer_exploration)
source $R/simenv.sh        # in a terminal, so a sim started by hand is visible to the rover tools
```

Run analysis (run folders are `tools/rover_mcp/runs/<date>_<name>/`, git-ignored):

```bash
python3 tools/rover_mcp/gates.py RUN_OR_EXPERIMENT_DIR...     # Must/stretch gates table per run
python3 tools/rover_mcp/compare.py EXP_DIR... [--out DIR]     # comparison.md + comparison.png
python3 docs/assets/nav_speed_2026-10-21/before_after.py RUN_DIR...   # validate.py-style p90 table
python3 docs/assets/nav_speed_2026-10-21/ceiling.py 0.22 OUT.npz      # coverage ceiling for a planner radius
python3 docs/assets/comparisons/make_figures.py               # redraw the Comparisons.md charts
```

**Simulation work goes through the `rover` MCP server** (`tools/rover_mcp/`, `.mcp.json`): any
request to run, watch, screenshot, debug, tune or compare the robot in Gazebo/RViz, or a report of
it spinning, stalling, leaving the path or not starting. Follow the `rover-tune` skill
(`.claude/skills/rover-tune/SKILL.md`): preflight → smoke_test → observe → diagnose → change one
thing → smoke_test → experiment. Do not hand-write launch/recorder/`pkill` scripts for this. If the
`mcp__rover__*` tools are not loaded, call them from a shell:
`tools/rover_mcp/.venv/bin/python tools/rover_mcp/mcp_call.py 'sim_start {}' 'observe {"seconds":60}'`.

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
