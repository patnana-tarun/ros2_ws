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
| MPU-9250 gyro | `/imu` | yaw rate | a skid-steer's wheels slide sideways when turning, so encoder yaw is unreliable |

- Not used: the magnetometer (motors and rock make it unreliable) and the accelerometers.
  Yaw therefore drifts slowly, and SLAM corrects it through `map → odom`.
- `two_d_mode` is on, and the output runs at 30 Hz.
- In simulation, Gazebo's DiffDrive publishes `/wheel/odom`. Its own transform goes to an
  unbridged topic, so only the EKF publishes `odom → base_footprint`.

## Measured in simulation (2026-09-26)
The robot was commanded 3.2 rad of turn on the spot before the track-width calibration.

| | True yaw | EKF | Wheel odometry alone |
|--|---------|-----|----------------------|
| After the turn | 82° | 83° | 184° |

The robot slipped, and the gyro caught it while the wheels did not. After a further 1 m leg,
the EKF position was within 5 cm of the truth.
