---
tags: [concept]
---
# Topics

This is the only place topics are listed.

## Mesh relay ([[mesh_nodes]])
| Dir | Topic              | Type           | Reliability | Durability      | Depth | Rate          |
|-----|--------------------|----------------|-------------|-----------------|-------|---------------|
| sub | `/map`             | `OccupancyGrid`| RELIABLE    | TRANSIENT_LOCAL | 1     | set by SLAM   |
| pub | `/mesh/map`        | `MeshMap`      | RELIABLE    | TRANSIENT_LOCAL | 1     | 1 per `/map`, every 3 s ([[Relay rates]]) |
| pub | `/mesh/map_status` | `SenderStatus` | RELIABLE    | VOLATILE        | 10    | 1 Hz + after each map |
| sub | `/tf`              | `TFMessage`    | BEST_EFFORT | VOLATILE        | 100   | ~100 /s from three sources ([[Relay rates]]) |
| pub | `/mesh/tf`         | `MeshTf`       | BEST_EFFORT | VOLATILE        | 100   | 1 per 3 `/tf`, per source: ~33 /s ([[Relay rates]]) |
| pub | `/mesh/tf_status`  | `SenderStatus` | RELIABLE    | VOLATILE        | 10    | 5 Hz ([[PDR measurement]]) |

Why the QoS differs: [[QoS design]].

## Receiver commands ([[Receiver (external)]])
| Dir | Topic              | Type              | Use |
|-----|--------------------|-------------------|-----|
| sub | `/mesh/logger_cmd` | `std_msgs/String` | `start` / `stop` / `exit` for `tf_rolling_metrics` ([[Run logging]]) |

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
Same as the Gazebo bridge above, from drivers instead: `/wheel/odom`, `/joint_states` and
`/imu` from `esp32_bridge` (which forwards `/cmd_vel` to the ESP32), and `/scan` from
`x2_lidar` (or `ydlidar_ros2_driver` with `lidar:=ydlidar`).

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

## Demo recording ([[Demo recording]])
| Dir | Topic | Type | Node |
|-----|-------|------|------|
| pub | TF `map → view_anchor` | `tf2_msgs/TFMessage` | `demo_view_box` (30 Hz; RViz view centre) |
| pub | `/demo/view_box` | `visualization_msgs/Marker` | `demo_view_box` (box outline) |
| pub/sub | `/demo_hud/update`, `/demo_hud/feedback` | interactive markers | `demo_hud` ↔ RViz (explored %, time; the drag comes back as feedback) |
| sub | `/map`, `/odom`, `/exploration_complete` | | `demo_hud` |
| sub | `/world/<world>/dynamic_pose/info` (Gazebo) | `gz.msgs.Pose_V` | `demo_chase_cam` |
| pub | `/gui/track` (Gazebo) | `gz.msgs.CameraTrack` | `demo_chase_cam` (30 Hz, FOLLOW mode) |
