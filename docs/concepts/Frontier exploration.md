---
tags: [concept]
source: src/explorer_exploration/explorer_exploration/frontier_tad_node.py
---
# Frontier exploration

How [[explorer_exploration]] decides where to go next. The source is Buriboev, Choi & Jeon
(2025), *"Optimized Frontier-Based Path Planning Using the TAD Algorithm"*, Electronics
14(1), 74, adapted to a raw occupancy grid.

## Loop
1. On every `/map` update, find **frontier cells**: free cells with an unknown 4-neighbour.
2. Group them into clusters with 8-connectivity, and drop clusters smaller than
   `min_frontier_size` (7 cells = 0.35 m, the paper's minimum frontier size).
3. Score each cluster (below), then publish the centroid of the best one as `/best_goal`.
4. `explore_coordinator` sends it to Nav2. While a goal is active, newer goals are
   ignored. The next goal is taken once Nav2 succeeds or gives up.
5. When no cluster is left, publish `/exploration_complete`.

## TAD score
| Term | Meaning on the grid | Paper |
|------|---------------------|-------|
| `d` distance  | straight line from the robot to the cluster centroid | Eq. 2, exact |
| `a` adjacent  | area of the unknown region the cluster borders | stands in for the paper's Rmap-rectangle overlap |
| `t` trapezoid | +1 if the cluster has more cells between `sensor_short_range` and `sensor_long_range` than within `sensor_short_range`, 0 if equal, −1 if fewer | Eq. 5, literal |

Each term is min-max normalised across the current candidates, then combined as
`w_d·d + w_a·a + w_t·t`. All weights default to 1, as in Eq. 6. `scoring_mode:=nearest`
switches to the classic nearest-frontier baseline.

## Unknown-gap filling (added for this robot)
At range, neighbouring YDLIDAR X2 rays land several cells apart (0.84° is 7 cm at 5 m), and
SLAM Toolbox needs 2 rays through a cell before marking it free. So before the robot moves,
the map is speckled with unknown cells between rays.

The original code treated every speckle as a frontier. In the cave, all the speckles merged
into one cluster whose centroid was the robot itself: Nav2 "reached" it at once and the robot
never moved.

`unknown_gap_fill` (default 2) closes these gaps before detection:
- A morphological closing (3 × 3, 2 iterations) of the mapped mask finds unknown cells
  enclosed by mapped ones.
- Those cells are counted as free, and they no longer count as unknown for `a`.

The result is that a tunnel mouth seen through sparse rays becomes one solid frontier. On the
first map of the cave, the result is exactly the three tunnel mouths of the start chamber.
`unknown_gap_fill:=0` gives the original behaviour, for comparing against earlier results.

## Other changes in the port
- The robot pose is looked up for `robot_frame`, which defaults to `base_footprint`.
  TurtleBot3 used `base_link`.
- `sensor_long_range` is now 6.0 m (X2), up from 3.5 m (TurtleBot3 LDS).
- The coordinator logs whether Nav2 succeeded, aborted or cancelled. Before, both
  outcomes printed the same message.
