---
tags: [robot]
source: src/explorer_description/urdf/explorer_gazebo.xacro
---
# Gazebo simulation

Gazebo Harmonic additions to the [[Robot model]], launched from [[explorer_description]]. Bridged
topics are listed in [[Topics]]. Every node in the launch uses `use_sim_time: true`.

| Plugin / sensor              | Config |
|------------------------------|--------|
| Wheel friction               | μ1 = μ2 = 1.0 on all 6 wheels |
| `DiffDrive` (skid-steer)     | 3 joints per side; separation 0.176 m; radius 0.0325 m; max 0.5 m/s, 3 rad/s, 1 m/s² |
|                              | `cmd_vel` in → `odom` and tf `odom → base_footprint` out at 30 Hz |
| `JointStatePublisher`        | wheel and bogie angles → `joint_states` → robot_state_publisher |
| `Sensors`                    | ogre2 renderer (needed by the GPU LiDAR) |
| `gpu_lidar` on `laser_frame` | 360 samples over 360°, 10 Hz, 0.12–8 m, Gaussian noise σ = 1 cm. Generic stand-in until the YDLIDAR model is known |

The visuals are basic primitives with no mesh files, so no `GZ_SIM_RESOURCE_PATH` is needed.

For an end-to-end test: this simulation → a SLAM node (e.g. slam_toolbox, not in this repo) →
[[mesh_nodes]] with `use_sim_time:=true`.

Simulation caveats are in [[Known limitations]].
