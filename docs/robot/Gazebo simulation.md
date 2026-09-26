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
| `DiffDrive` (skid-steer)     | 3 joints per side; **effective** separation 0.43 m (below); radius 0.0325 m; max 0.5 m/s, 3 rad/s, 1 m/s² |
|                              | `cmd_vel` in → `wheel/odom` out at 30 Hz. Its TF goes to an unbridged topic; the EKF publishes `odom → base_footprint` ([[Odometry fusion]]) |
| `JointStatePublisher`        | wheel and bogie angles → `joint_states` → robot_state_publisher |
| `Sensors`                    | ogre2 renderer (needed by the GPU LiDAR) |
| `Imu` + `imu` on `imu_link`  | MPU-9250: 100 Hz; gyro σ 0.0012 rad/s, bias 0.0005; accel σ 0.021 m/s², bias 0.05 (datasheet noise densities at 100 Hz) |
| `gpu_lidar` on `laser_frame` | YDLIDAR X2: 430 samples over 360°, 7 Hz, 0.12–8 m, Gaussian noise σ = 1 cm |

**Effective track width.** Turning on the spot, a skid-steer's wheels slide sideways. With the
geometric 0.176 m, the robot reached only about 35 % of the commanded yaw rate (0.10 of 0.30,
0.22 of 0.60 rad/s). Setting the plugin's separation to 0.176 / 0.35 = 0.50 m gave 0.99–1.01
of the command up to 0.6 rad/s. After the chassis was flipped (bogie in front) and the torque
limit set to stall, 0.50 m gave 1.16–1.18×, so it is now 0.50 / 1.17 = **0.43 m**: 1.08, 0.96
and 0.90 of the command at 0.3, 0.6 and 1.0 rad/s.

**Torque.** With the motor's rated 0.034 N·m as the joint limit the robot drove straight but
could not pivot at all. The four corner wheels drag sideways, needing about 0.67 N·m against
about 0.56 N·m from six motors. The limit is the stall torque, assumed 0.078 N·m
([[Robot model]]). A test with sideways friction lowered to 0.5 still did not pivot, and was
reverted. The real robot's motor driver needs the
same kind of calibration: measure turn rate against command, and divide.

**`/cmd_vel` message type.** A bridge connects to only one ROS type per topic, and a
publisher of a different type is silently ignored. The launch argument `cmd_vel_stamped` picks
the type:
- `true` (default): `TwistStamped`, as published by the Jazzy `turtlebot3_teleop`
- `false`: `Twist`, as published by `teleop_twist_keyboard` and by Nav2 on Jazzy by default

To check a mismatch, run `ros2 topic info /cmd_vel -v`: the publisher and the bridge must show
the same type.

The robot's visuals are basic primitives with no mesh files. `gui:=false` runs Gazebo headless
(server with headless rendering, which the GPU LiDAR needs).

**Worlds.** `world:=` accepts `empty.sdf` (the default), `cave.sdf`, `cave_open.sdf` (see
[[Cave world]]) or a path. The launch file adds the package's `worlds/` and `models/` to
`GZ_SIM_RESOURCE_PATH`. The spawn pose is set with `x:=`, `y:=` and `yaw:=`.

For an end-to-end test: this simulation → a SLAM node (e.g. slam_toolbox, not in this repo) →
[[mesh_nodes]] with `use_sim_time:=true`.

Simulation caveats are in [[Known limitations]].
