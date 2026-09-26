# explorer_exploration

Frontier detection + TAD scoring + Nav2 goal sending, for the Explorer
robot software milestone (find the best next spot, autonomously).

ROS 2 Jazzy, Gazebo Harmonic, Nav2, SLAM Toolbox. Ported from the earlier
ROS 2 Humble / TurtleBot3 version on 2026-09-26; design notes live in the
workspace's `docs/` vault (`packages/explorer_exploration.md`,
`concepts/Frontier exploration.md`, `concepts/Navigation stack.md`).

## Build

```bash
cd ~/ros2_ws
colcon build --packages-select explorer_description explorer_exploration
source install/setup.bash
```

## Run everything with one command

```bash
ros2 launch explorer_exploration bringup.launch.py              # cave.sdf
ros2 launch explorer_exploration bringup.launch.py world:=cave_open.sdf
```

This brings up Gazebo with the explorer robot (from `explorer_description`,
including the wheel-odometry + IMU EKF), SLAM Toolbox, Nav2, our
frontier/TAD nodes, and RViz2 together. No manual "2D Pose Estimate" is
needed - Nav2 takes its map and the `map -> odom` transform from SLAM Toolbox
instead of running its own map_server + AMCL, which is the correct pairing
for explore-while-mapping.

SLAM Toolbox is started by `bringup.launch.py` itself and activated by
Nav2's lifecycle manager (nav2_bringup gets `use_localization:=False`). See
the docstring in `launch/bringup.launch.py` for why.

Headless, with the metrics logger (for scripted A/B runs):
```bash
ros2 launch explorer_exploration benchmark_headless.launch.py scoring_mode:=nearest
```

Just the exploration nodes, on top of a SLAM + Nav2 stack you started yourself:
```bash
ros2 launch explorer_exploration explore.launch.py
```

## Watching it work in RViz2

`bringup.launch.py` opens Nav2's default RViz view. Add:
- `MarkerArray` on `/frontier_markers` - orange spheres are candidates,
  green is the one it picked
- `LaserScan` on `/scan` (optional, sanity check)

## Tuning the TAD weights

Edit the parameters in `launch/explore.launch.py`, or override at launch time:
```bash
ros2 launch explorer_exploration explore.launch.py \
  w_distance:=1.0 w_adjacency:=1.5 w_trapezoid:=0.8
```

Nav2 and SLAM Toolbox parameters for this robot are in
`config/nav2_params.yaml` (footprint, speeds, MPPI controller, X2 LiDAR
ranges); every value that differs from Nav2's Jazzy defaults is commented.

Notes on the current implementation vs. Buriboev, Choi & Jeon (2025),
*"Optimized Frontier-Based Path Planning Using the TAD Algorithm"*,
Electronics 14(1), 74:
- `d` (distance, Eq. 2) is exact - straight-line distance, robot pose to
  frontier centroid. Same formula as the paper.
- `a` (adjacent) is the size of the connected unknown-cell region the
  frontier cluster borders. The paper defines `a_n` over overlap between
  Rmap rectangles (a mapping scheme this project doesn't build); this is
  the closest grid equivalent to their own description of what a high
  `a_n` means - "the corresponding frontier encompasses a larger
  unexplored area."
- `t` (trapezoid, Eq. 5) follows the paper's rule literally: compare the
  frontier's cell count within the robot's long sensor range (`outer`,
  `sensor_long_range`, 6.0 m for the YDLIDAR X2) against its cell count
  within short range (`inner`, `sensor_short_range`). `t_n = 1` if
  outer > inner (widening, worth exploring), `0` if equal, `-1` if
  outer < inner (narrowing/dead end).
- The paper sums the three unweighted (`F_n = d_n + a_n + t_n`, Eq. 6)
  because its d/a/t all live in comparable Rmap-rectangle units. Ours
  don't - `d` is metres, `a` is square metres, `t` is {-1,0,1} - so we
  min-max normalize each across the current candidates before applying
  `w_distance`/`w_adjacency`/`w_trapezoid`. Weights default to 1.0 (Eq. 6
  parity) and are tunable per the section above.
- `unknown_gap_fill` (default 2, added in the port): unknown cells enclosed
  by mapped cells - gaps between LiDAR rays - are counted as free before
  frontier detection. Without it the first scan's speckle forms one
  frontier cluster centred on the robot and the robot never moves. Set it
  to 0 for the original behaviour.

## Known rough edges to watch for while testing

- If the robot hasn't published a `map` -> `base_footprint` transform yet
  (e.g. right at startup), the node logs a warning and skips that cycle -
  this is expected for the first second or two.
- The first goal is often rejected because Nav2 is not active yet; the
  next `/map` update retries it.
- `min_frontier_size` filters out tiny noisy frontier specks - raise it if
  you see the robot chasing single-cell artifacts near walls.
- The coordinator ignores new goals while mid-navigation. It logs whether
  Nav2 succeeded or gave up; if it looks "stuck" on an old goal, check
  Nav2's own logs first.
- The 2D LiDAR only sees obstacles that cross its scan plane (0.18 m).
  Low rocks in the cave are invisible to it and can catch the robot.
