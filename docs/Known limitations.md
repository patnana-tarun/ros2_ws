---
tags: [issue]
---
# Known limitations

| # | Area | Issue | Possible fix |
|---|------|-------|--------------|
| 1 | Relay | `/tf_static` is not relayed, so the receiver never gets `base_link → laser_frame` and the other fixed frames | receiver runs its own robot_state_publisher, or relay `/tf_static` |
| 2 | Relay | All of `/tf` is forwarded. In simulation that includes 6 wheel and 2 bogie transforms, which means heavy mesh traffic | filter by frame (e.g. keep `map→odom`, `odom→base_footprint`) |
| 3 | Relay | The throttle counts messages, not bytes or time | throttle by rate or bytes if needed |
| 4 | Relay | Fixed hold time instead of confirmed delivery ([[Map-in-flight throttle]]) | receiver ACK topic |
| 5 | Relay | Parameters are read only at startup | add a parameter callback |
| 6 | Interfaces | `MeshScan` wraps `OccupancyGrid` and its field order differs from `MeshMap` ([[my_mesh_interfaces]]) | fix it before first use |
| 7 | Sim | Skid-steer `/odom` drifts on turns because DiffDrive assumes no slip ([[Gazebo simulation]]) | rely on SLAM correction |
| 8 | Model | All masses and the LiDAR/Pi sizes are assumed ([[Robot model]]) | weigh and measure the parts |
| 9 | Sim | The LiDAR is a generic model | update once the YDLIDAR model is known |
| 10 | Verification | The Gazebo launch has not been run end-to-end yet ([[2026-09-26]]) | run it |
