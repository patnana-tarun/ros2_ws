---
tags: [robot]
source: src/explorer_bringup/explorer_bringup/esp32_bridge.py
---
# esp32_bridge

The Pi-side node that talks to the ESP32 ([[Serial protocol]]) and gives ROS the same topics
as the simulation ([[Topics]]).

| Dir | Topic | Type | Notes |
|-----|-------|------|-------|
| sub | `/cmd_vel` | `geometry_msgs/TwistStamped` | from Nav2 or `manual_drive` |
| pub | `/wheel/odom` | `nav_msgs/Odometry` | 50 Hz; the EKF uses vx and vy (= 0) |
| pub | `/imu` | `sensor_msgs/Imu` | 50 Hz, frame `imu_link`, no orientation (covariance −1) |
| pub | `/joint_states` | `sensor_msgs/JointState` | wheel angles for RViz; bogie joints 0 (not sensed) |

## What it does
- **Commands:** `/cmd_vel` (v, ω) → side speeds `v ∓ ω·track/2` with the **effective** track
  width, sent as `S,<left>,<right>` at `cmd_rate`. No `/cmd_vel` for `cmd_timeout` → sends 0.
- **Wheel odometry:** from the differences of the travel totals and the ESP32's own `ms`
  (so Pi scheduling jitter doesn't enter the speeds). Side distance = mean of front and rear;
  vx = mean of the sides / dt. The pose it integrates is for `/joint_states` only; the EKF
  ignores it.
- **Slip check:** if a side's front and rear wheel moved more than `slip_ratio` (30 %) apart in
  one step, vx goes out with variance 0.25 instead of 0.002. The EKF then follows its own
  prediction and the gyro rather than a spinning or lifted wheel ([[Odometry fusion]]).
- **IMU:** passes gyro and accel through in the chip's axes with fixed covariances;
  robot_localization rotates them by the URDF's `imu_joint`.
- **Robustness:** opens the port with DTR/RTS low (the DevKit then doesn't reset), reconnects
  every few seconds after an unplug, restarts its reference when the ESP32 reboots. Every 5 s
  it warns if no valid telemetry came (wrong port, firmware missing, still booting), the IMU
  is missing, or the drive is disabled (`TICKS_PER_REV` = 0). ESP32 `#` messages appear in its
  log as `ESP32: ...`.
- `mock:=true` simulates a perfect ESP32 inside the node (no serial). For a realistic test use
  [[Hardware test tools]] (`fake_robot`).

## Parameters (`config/robot.yaml`)
| Name | Default | Meaning |
|------|---------|---------|
| `port` | `/dev/ttyUSB0` (launch: `esp_port`) | device or pyserial URL (`socket://host:port`) |
| `baud` | 115200 | must match `BAUD` in `config.h` |
| `track_width` | 0.43 | effective skid-steer track (m), from simulation; calibrate ([[Hardware bring-up]]) |
| `wheel_radius` | 0.0325 | for the wheel angles only |
| `cmd_timeout` | 0.5 | s without `/cmd_vel` before sending 0 |
| `cmd_rate` | 20 | `S` lines per second |
| `slip_ratio` | 0.3 | front/rear disagreement that counts as slip |
| `imu_frame` | `imu_link` | frame of `/imu` |
| `gyro_variance` | 4e-6 | (0.002 rad/s)², ICM-20948 at its ~50 Hz filter |
| `accel_variance` | 3e-4 | (0.017 m/s²)² |
| `mock` | false | simulated ESP32 inside the node |
