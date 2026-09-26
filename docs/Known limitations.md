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
| 7 | Sim | Yaw from the EKF drifts slowly: gyro only, no magnetometer ([[Odometry fusion]]) | SLAM corrects it through `map → odom` |
| 8 | Model | All masses and the LiDAR/Pi sizes are assumed ([[Robot model]]) | weigh and measure the parts |
| 9 | Sim | The X2 model uses datasheet figures. Real X2 noise and dropouts on dark, wet rock are unknown | compare with a real scan |
| 10 | Sim | In the [[Cave world]] the LiDAR sees the visual wall a few cm behind the collision wall | lower `COLLISION_Z` if it matters |
| 11 | Sim | Cave lamps cast no shadows, so light leaks through rock into neighbouring passages | shadowed lights (slower) |
| 12 | Sim | The cave layout is fixed. `--seed` only changes rock detail, not the chambers or tunnels ([[Cave world]]) | randomise `CHAMBERS`/`TUNNELS` for training variety |
| 13 | Sim | The closed cave is dark, and the robot has no camera or headlight | add them if vision is needed |
| 14 | Navigation | The 2D LiDAR only sees what crosses its scan plane at 0.18 m. Rocks lower than that are invisible to it, and the robot can only climb about 5–6 cm ([[Rock climbing]]). Rocks between about 6 and 18 cm can therefore stop it unseen; in an earlier cave it got high-centred on a 7.8 cm boulder. The [[Cave world]] now has only LiDAR-level rocks (user's choice for testing) | depth camera, a tilted second LiDAR or bumpers |
| 15 | Robot | The effective track width (0.43 m) was measured in simulation only ([[Gazebo simulation]]) | measure turn rate against command on the real robot |
| 19 | Robot | Motor stall torque is assumed (0.8 kg·cm). With the rated 0.35 kg·cm the simulated robot can't pivot at all ([[Robot model]]) | datasheet stall torque; test a pivot on rock with the real robot |
| 20 | Robot | Leading with the bogie climbed worse than leading with the rocker in simulation ([[Rock climbing]]) | compare both on the real robot |
| 16 | Robot | No driver exists yet for the real encoders and IMU. The EKF expects `/wheel/odom` and `/imu` ([[Odometry fusion]]) | write the firmware/driver |
| 17 | Robot | LM393 slot encoders are single-channel, so they count pulses but can't tell direction | take direction from the commanded wheel speed |
| 18 | Model | IMU height on the plate is assumed ([[Robot model]]) | measure it |
