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

Because `d` is normalised and *added*, a larger distance gives a higher score: on its own, TAD
prefers the farthest frontier. The earlier offline benchmark points the same way: the tuned
TAD there set `w_distance` to 0 (`comparison/benchmark_log.txt`). The scores are left as they
are; the depth-first selection below decides which frontiers may be chosen.

## Depth-first selection (`selection_mode: dfs`, default)
Suggested by the user (2026-09-26). With the original "best score anywhere", the robot left a
branch half-explored whenever a better-scoring frontier appeared elsewhere, and had to come
all the way back later.

1. **Travel distance.** A shortest-path (Dijkstra) search over free cells from the robot
   gives the travel distance to every frontier. Cells next to an obstacle are excluded, so
   paths don't squeeze through gaps. In a cave the straight-line distance misleads: a
   frontier just behind a wall can be close as the crow flies but far to drive to.
2. **Eligible frontiers.** Only frontiers whose travel distance is at most
   `max(dfs_ratio × nearest, nearest + dfs_margin)` can be chosen, where `nearest` is the
   travel distance to the nearest frontier. Defaults are 1.5 and 2 m. Unreachable frontiers
   are dropped.
3. **Choice.** The best TAD score among the eligible frontiers wins, so the robot keeps going
   in the branch it's in.
4. **Backtracking.** When the branch is finished (a dead end), the nearest remaining frontier
   is the branch it passed most recently, so the robot backs up to it, like DFS.

5. **Rock shadows are skipped.** Each rock casts a LiDAR shadow: a small unknown pocket
   enclosed by free space and the rock. Frontiers whose unknown region (`a`) is smaller than
   `min_pocket_area` (1 m²) are skipped in this mode. Without that, preferring near frontiers
   made the robot tour every rock in a chamber. A real opening borders the large unexplored
   rest of the cave instead.

In RViz, frontiers outside the window are grey, candidates orange, and the chosen one green.
`selection_mode:=global` gives the original behaviour.

## Goals that fail
- **Placement.** In `dfs` mode the goal is the reachable frontier cell nearest to the cluster
  centroid, not the centroid itself, which can fall among rocks or inside a wall.
- **Timeout.** `explore_coordinator` abandons a goal after max(60 s, 15 s per metre).
- **Blacklist.** Aborted or timed-out goals go on `/frontier_blacklist`, and the frontier node
  skips frontiers within 0.5 m of them for 5 min. Before this, one unreachable frontier among
  rocks kept the robot busy for 9 min.

## Comparison (2026-09-27)
Headless runs in the [[Cave world]], 30 min cap, same settings apart from the selection. The
true open floor is 83.1 m².

| Selection | 5 min | 10 min | 15 min | End | Finished? |
|-----------|-------|--------|--------|-----|-----------|
| `global` (original TAD) | 24.1 m² | 60.8 | 67.6 | 77.4 m² at 30 min | no. At 20 min it went back to the D dead end it had passed early on |
| `dfs` without the shadow filter | 24.0 | 31.0 | 32.5 | 73.4 m² at 30 min | no. It spent minutes 10–25 touring rock shadows in chamber B |
| **`dfs` (default)** | 62.0 | 72.8 | 77.1 | **78.0 m² (94 %) at ≈ 23 min** | **yes**: `/exploration_complete` |

![[slam_map_cave_dfs.png]]
*The final `dfs` map: all six chambers, the three dead ends and both loops.*

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
