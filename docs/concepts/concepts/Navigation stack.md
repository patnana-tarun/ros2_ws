---
tags: [concept]
source: src/explorer_exploration/config/nav2_params.yaml
---
# Navigation stack

The SLAM and Nav2 setup that [[explorer_exploration]] drives. It is Nav2 on ROS 2 Jazzy,
configured in `config/nav2_params.yaml` and started by `bringup.launch.py`.

```
/scan ──► SLAM Toolbox (sync) ──► /map, TF map→odom
/odom, TF odom→base_footprint ◄── EKF ([[Odometry fusion]])
/best_goal ──► navigate_to_pose ──► NavFn planner ──► MPPI controller ──► velocity smoother
          ──► collision monitor ──► /cmd_vel (TwistStamped) ──► Gazebo DiffDrive / motor driver
```

## Choices and why
| Setting | Value | Why |
|---------|-------|-----|
| Footprint | 0.32 × 0.22 m rectangle | collision boxes are ±0.152 × ±0.10 m, plus 1 cm per side |
| Inflation | radius 0.22 m, cost scaling 12 | just past the circumscribed radius (0.194 m), so only a ~0.1 m cost band is left beyond the inscribed zone. 0.35 m / 6 merged wall and rock inflation into one high-cost field and MPPI dithered; 0.30 m / 10 still closed the gaps between chamber rocks (2026-10-05). The thick dark bands in RViz are mostly the inscribed zone (half the robot's width), which only a smaller footprint could shrink |
| Controller | MPPI, 1000 samples × 40 steps at 15 Hz, `wz_std` 0.3, TwirlingCritic on | Regulated Pure Pursuit was tried first (lighter). With the goal directly behind the robot its rotate-in-place flipped direction every cycle, so the robot never turned round. TwirlingCritic penalises back-and-forth turning |
| Replanning | path kept 4 s, replanned at once if it gets blocked (`behavior_trees/explore_nav_to_pose.xml`) | every 1 s flipped the path around rocks and the robot kept turning (2026-09-26); 10 s kept it on its first route after a better side passage appeared (2026-10-05) |
| Recovery | BackUp 0.3 m first, then clear costmaps, spin, wait; progress timeout 15 s | a skid-steer robot wedged between rocks can't pivot out. With Nav2's order and a 30 s progress timeout, the coordinator's goal timeout always fired before BackUp ran |
| Speed limits | 0.2 m/s forward, 0.1 m/s reverse, 0.6 rad/s | narrow tunnels. The skid-steer tracks yaw commands exactly up to 0.6 rad/s ([[Gazebo simulation]]) |
| Goal tolerance | 0.4 m, yaw ignored (2π; GoalAngleCritic off) | frontier centroids often sit against a wall inside the inflation. At 0.25 m the robot spent over 3 min on one goal. Frontier goals carry no meaningful heading |
| Progress checker | 0.3 m within 30 s | pivots don't count as movement |
| Planner | NavFn, `allow_unknown: true` | frontier goals sit at the edge of unknown space |
| Costmap sensor | `/scan`, obstacles to 4 m, clearing to 5 m | YDLIDAR X2 range 0.12–8 m |
| `cmd_vel` | `TwistStamped` (`enable_stamped_cmd_vel`) | matches the Gazebo bridge default and the Jazzy teleop |
| SLAM | sync mode, 0.05 m, laser 0.12–7.5 m, map update every 2 s, 0.2 m / 0.2 rad between scans | X2 range. Small, slow robot. The frontier node re-plans on every `/map` |

## Result
![[slam_map_cave_run11.png]]
*Autonomous run in the [[Cave world]], 2026-09-26: SLAM Toolbox + Nav2 + TAD, headless,
30 min cap. The robot mapped 75.7 of 83.1 m² of open floor (91 %): all chambers except F,
which it was entering when time ran out. Both loops closed consistently, and the rocks show as
islands. Nav2 reached 9 goals and aborted 1. The turn command reversed 38 times in 30 min.*

Before the replanning, inflation and TwirlingCritic changes, and with a rock misplaced in the
A→B tunnel, the same stack stalled at 16–32 m², turning back and forth in front of rocks.
## How SLAM is started
`bringup.launch.py` starts SLAM Toolbox and the map saver itself, and brings them up with
Nav2's lifecycle manager. It runs `nav2_bringup` with `use_localization:=False`.

Why not `nav2_bringup slam:=True`: that path activates SLAM Toolbox from a launch-event
handler, which races under CPU load. In one of the test runs SLAM Toolbox was configured
but never activated. The `map` frame never appeared, and Nav2 aborted its bringup.
