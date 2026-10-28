---
tags: [robot]
source: src/explorer_description/config/ekf.yaml
---
# Odometry fusion

The robot's `/odom` and `odom → base_footprint` come from a `robot_localization` EKF that
fuses wheel odometry and the IMU. The same config is meant for the real robot. Sensors are
listed in [[Robot model]].

| Input | Topic | Fields used | Why |
|-------|-------|-------------|-----|
| Wheel odometry (encoders) | `/wheel/odom` | vx, vy (= 0) | forward speed. vy = 0 is the no-sideways-motion constraint |
| IMU gyro (MPU-9250 in simulation, ICM-20948 on the robot) | `/imu` | yaw rate | a skid-steer's wheels slide sideways when turning, so encoder yaw is unreliable |

- Not used: the magnetometer (motors and rock make it unreliable) and the accelerometers.
  Yaw therefore drifts slowly, and SLAM corrects it through `map → odom`.
- `two_d_mode` is on, and the output runs at 30 Hz. From 2026-10-06 to 2026-10-15 it ran at 10 Hz
  for the mesh relay, which made the startup turn overshoot badly ([[Baseline runs 2026-10-08]]).
  The relay now thins TF for the mesh instead ([[Relay rates]]).
- On the robot, [[esp32_bridge]] raises the vx variance while a wheel slips, so the EKF trusts
  the wheels less then. The robot's EKF also runs with `predict_to_current_time: true` (set in
  `robot.launch.py`, not here): with the ESP32's 50 Hz telemetry some 30 Hz cycles have no new
  measurement, and without it `/odom` came out at 20 Hz (measured 2026-10-28).
- In simulation, Gazebo's DiffDrive publishes `/wheel/odom`. Its own transform goes to an
  unbridged topic, so only the EKF publishes `odom → base_footprint`.

## Measured in simulation (2026-09-26)
The robot was commanded 3.2 rad of turn on the spot before the track-width calibration.

| | True yaw | EKF | Wheel odometry alone |
|--|---------|-----|----------------------|
| After the turn | 82° | 83° | 184° |

The robot slipped, and the gyro caught it while the wheels did not. After a further 1 m leg,
the EKF position was within 5 cm of the truth.
