---
tags: [concept, reference]
---
# Topics

This is the only place topics are listed.

## Mesh relay ([[mesh_nodes]])
| Dir | Topic              | Type           | Reliability | Durability      | Depth | Rate          |
|-----|--------------------|----------------|-------------|-----------------|-------|---------------|
| sub | `/map`             | `OccupancyGrid`| RELIABLE    | TRANSIENT_LOCAL | 1     | set by SLAM   |
| pub | `/mesh/map`        | `MeshMap`      | RELIABLE    | TRANSIENT_LOCAL | 1     | 1 per `/map`  |
| pub | `/mesh/map_status` | `SenderStatus` | RELIABLE    | VOLATILE        | 10    | 1 Hz          |
| sub | `/tf`              | `TFMessage`    | BEST_EFFORT | VOLATILE        | 100   | set by tf sources |
| pub | `/mesh/tf`         | `MeshTf`       | BEST_EFFORT | VOLATILE        | 100   | ≤ 1 per `/tf` ([[Map-in-flight throttle]]) |
| pub | `/mesh/tf_status`  | `SenderStatus` | RELIABLE    | VOLATILE        | 10    | 5 Hz ([[PDR measurement]]) |

Why the QoS differs: [[QoS design]].

## Gazebo bridge ([[Gazebo simulation]])
| Topic           | Type                     | Direction    |
|-----------------|--------------------------|--------------|
| `/clock`        | `rosgraph_msgs/Clock`    | Gazebo → ROS |
| `/cmd_vel`      | `geometry_msgs/TwistStamped` (default) or `Twist`, set by `cmd_vel_stamped` | ROS → Gazebo |
| `/wheel/odom`   | `nav_msgs/Odometry`      | Gazebo → ROS |
| `/imu`          | `sensor_msgs/Imu`        | Gazebo → ROS (frame `imu_link`) |
| `/joint_states` | `sensor_msgs/JointState` | Gazebo → ROS |
| `/scan`         | `sensor_msgs/LaserScan`  | Gazebo → ROS (frame `laser_frame`) |

`/robot_description`, `/tf` and `/tf_static` are published by robot_state_publisher.

## Odometry ([[Odometry fusion]])
| Dir | Topic | Type | Node |
|-----|-------|------|------|
| sub | `/wheel/odom`, `/imu` | `Odometry`, `Imu` | `ekf_filter_node` |
| pub | `/odom` + TF `odom → base_footprint` | `Odometry` | `ekf_filter_node` (remapped from `odometry/filtered`) |

## Real robot ([[explorer_bringup]])
Same as the Gazebo bridge above, from drivers instead: `/wheel/odom` and `/joint_states`
from `explorer_base`, `/imu` from `mpu9250_imu`, and `/scan` from `ydlidar_ros2_driver`.
`/cmd_vel` goes into `explorer_base`.

## Exploration ([[explorer_exploration]])
| Dir | Topic | Type | Node |
|-----|-------|------|------|
| sub | `/map` (TRANSIENT_LOCAL) | `OccupancyGrid` | `frontier_tad_node`, `metrics_logger` |
| pub | `/best_goal` | `PoseStamped` | `frontier_tad_node` |
| pub | `/frontier_markers` | `MarkerArray` | `frontier_tad_node` (orange = candidates, green = chosen) |
| pub | `/exploration_complete` | `std_msgs/Empty` | `frontier_tad_node` |
| pub/sub | `/manual_override` | `std_msgs/Bool` | `manual_drive` → `explore_coordinator` (heartbeat 5 Hz; `false` = resume now) |
| pub | `/cmd_vel_nav` | `TwistStamped` | `manual_drive` (Nav2's controller output, into the velocity smoother) |
| action | `navigate_to_pose` | `nav2_msgs/NavigateToPose` | `explore_coordinator` → Nav2 |
| pub | `/cmd_vel` | `TwistStamped` | Nav2 collision monitor ([[Navigation stack]]) |
