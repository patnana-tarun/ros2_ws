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
| `/cmd_vel`      | `geometry_msgs/Twist`    | ROS → Gazebo |
| `/odom`         | `nav_msgs/Odometry`      | Gazebo → ROS |
| `/tf`           | `tf2_msgs/TFMessage`     | Gazebo → ROS |
| `/joint_states` | `sensor_msgs/JointState` | Gazebo → ROS |
| `/scan`         | `sensor_msgs/LaserScan`  | Gazebo → ROS |

`/robot_description`, `/tf` and `/tf_static` are also published by robot_state_publisher.
