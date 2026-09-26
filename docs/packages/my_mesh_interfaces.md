---
tags: [package]
path: src/my_mesh_interfaces
build_type: ament_cmake
---
# my_mesh_interfaces

Message definitions for the mesh link. Every message except `SenderStatus` wraps a standard ROS
message in the [[Message envelope]].

| Message        | Wraps                    | Extra field           | Used by        |
|----------------|--------------------------|-----------------------|----------------|
| `MeshMap`      | `nav_msgs/OccupancyGrid` | –                     | [[mesh_nodes]] |
| `MeshTf`       | `tf2_msgs/TFMessage`     | `bool map_in_flight` ([[Map-in-flight throttle]]) | [[mesh_nodes]] |
| `SenderStatus` | –                        | `uint64 last_sequence_sent` ([[PDR measurement]]) | [[mesh_nodes]] |
| `MeshScan`     | `nav_msgs/OccupancyGrid` | –                     | nothing yet    |

`MeshScan` wraps an `OccupancyGrid`, not a `LaserScan` as the name suggests, and its fields
are in a different order from `MeshMap` (see [[Known limitations]]).

```bash
colcon build --packages-select my_mesh_interfaces
ros2 interface show my_mesh_interfaces/msg/MeshTf
```
