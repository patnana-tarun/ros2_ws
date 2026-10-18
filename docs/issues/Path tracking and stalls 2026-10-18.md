---
tags: [issue]
---
# Path tracking and stalls 2026-10-18

Why the robot seems to leave the planned path, and where the "Control loop missed its desired
rate … 7 Hz" warning comes from. Measured on the live sim (cave world, RTX rendering), with probe
nodes that compare `/plan`, TF, `/cmd_vel*`, `/odom`, the local costmap and Gazebo's true pose.
Nav2 settings are in [[Navigation stack]].

## 1. It stalls on the path rather than drifting off it
Over 150 s, the cross-track error from `/plan` (in the SLAM pose) was 1.4 cm median, 2.8 cm
p90 and 24 cm max. It was above 6 cm only 1.9 % of the time. The commands came through intact:
the collision monitor never cut speed, and the velocity smoother changed `wz` by less than
0.002 rad/s. The achieved yaw rate matched the command with about 0.25 s lag.

The visible departures come from stalls. In the 15 s before each of 5 "Failed to make progress"
errors, MPPI commanded |vx| < 0.02 m/s in 73–92 % of cycles, alternating forward and back, while
the robot sat 3–5 cm from the path. The progress checker then aborted, and BackUp or Spin moved
the robot off the path (one BackUp ended with "Collision Ahead"). Before the restart there were
6–9 of these per 6 min ([[2026-10-18]]).

## 2. Why it stalls: the path isn't drivable for this footprint
Three stalls were caught live, all at the same rock (odom ≈ 8.3, −8.0):
- The robot's footprint was 0–2.5 cm from obstacle cells at a front corner, and 25–28 footprint
  cells were at inscribed cost.
- The path turned 65–128° away from the robot's heading.
- A front corner was 0.188 m from the centre, inside the 0.194 m circumscribed radius. So
  pivoting in place would sweep that corner into the rock, and BackUp was blocked behind as
  well.

The cause is on the planner side:
- **NavFn plans for a round robot.** It only keeps the path centre out of the inscribed zone
  (0.11 m, half the width). Corners and the turning circle (0.194 m) are ignored. With inflation
  at 0.22 m / 12, the cost slope is too short to push the path away from rocks. Along the stalled
  path, footprint cells stayed at cost 47–75 (scale 0–100) for the first 0.9 m.
- **The path is jagged.** NavFn's raw gradient path (2.7 cm spacing) changes heading by 20–45°
  every 5 cm. `smoother_server` runs, but the BT never calls it.
- **NavFn leaves every pose at heading 0.** That matters for item 4.

## 3. Little holds the robot to the path line
`PathAlignCritic` (weight 14) only scores once some sampled trajectory reaches
`offset_from_furthest` = 20 path points = 0.54 m along the path. With 40 steps × 0.07 s ×
0.2 m/s, the farthest any trajectory can reach is 0.56 m. So the critic only applies when driving
straight at full speed. Otherwise only `PathFollowCritic` acts: it pulls the trajectory end
toward a point about 13 cm past the furthest reached point, which cuts corners. The early
returns are in Jazzy's `path_align_critic.cpp`.

## 4. Replanning every 0.53 s, not every 4 s
227 plans arrived in 150 s. In 10 of 13 sampled cases the plan being replaced failed
`is_path_valid`. In footprint mode, Jazzy's planner server marks a path invalid if the footprint
hits a lethal cell at any remaining pose, and with NavFn every pose has heading 0. That defeats
the 4 s path hold. Most replans changed the path by about 1 cm (median), but some flipped it
(1 of 13 moved 1.39 m).

## 5. SLAM corrections move the robot relative to the path
`map → odom` jumped more than 5 cm 9 times in 150 s (max 23 cm, yaw < 1°). 36 % of the
off-path samples came within 1 s of such a jump, against 9.6 % of all samples. Separately, the
SLAM pose differed from Gazebo's truth by a world-fixed (−0.03, −0.19) m, the slow map drift of
[[Odometry fusion]]. Robot, map and path share that frame, so it doesn't cause tracking error.

## 6. The "7 Hz" warning
The controller runs at 14.6 Hz (median gap 67 ms, p99 100 ms). The warning only fires on the
**first cycle after a FollowPath abort**: 9 of 14 such restarts, none of 23 normal goal starts.
`ClearLocalCostmap-Context` in `explore_nav_to_pose.xml` wipes the local costmap, and the loop
waits (`isCurrent()`) for the next update, which comes at most 143 ms later at 7 Hz. Measured
cycles were 72–152 ms. The loop is paced by wall time, but the printed rate is
1 / (that cycle's sim-time duration). So the warning is a side effect of the aborts, not a slow
controller. Moving rendering to the GPU didn't change it.

## Candidate fixes
- A footprint-aware planner that produces headings: Smac Hybrid-A* or Lattice. Or keep NavFn and
  add `SmoothPath` to the BT. Either fixes items 2 and 4. Smac Lattice was tested in
  [[Planner comparison 2026-10-18]]: much better paths, but on its own no faster exploration.
- MPPI: `PathAlignCritic.offset_from_furthest` of about 8 (0.2 m), or a longer horizon. Fixes
  item 3.
- A longer cost slope from the inflation layer, so paths stay off rocks. Trade-off: the gap
  closures recorded in [[Navigation stack]].
