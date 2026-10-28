---
tags: [moc]
---
# Hardware files

## In the repo: `src/explorer_bringup/`
| Path | What |
|------|------|
| `firmware/explorer_esp32/` | the controller firmware ([[ESP32 firmware]]): `config.h`, `motors.h`, `encoders.h`, `imu.h`, `pilink.h`, `explorer_esp32.ino` |
| `firmware/rover_tests/1_…7_*/` | the user's step-by-step test sketches (motors, IMU, encoders, PID, heading, odometry, full system). Used in [[Hardware bring-up]] step 1 |
| `firmware/icm20948_calibration/` | ICM-20948 test and calibration (accel 6-face, mag), saves to flash for the controller |
| `firmware/rssi_sniffer/` | the field tests' RSSI sniffer (`rssi_sniffer.ino`) and its PC logger (`rssi_csv_logger.py`), kept for [[RSSI merge plan]] |
| `explorer_bringup/esp32_bridge.py` | [[esp32_bridge]] |
| `explorer_bringup/x2_lidar.py` | [[x2_lidar]] |
| `explorer_bringup/fake_robot.py`, `checks.py`, `selftest.py` | [[Hardware test tools]] |
| `launch/robot.launch.py` | robot_state_publisher + bridge + EKF + LiDAR; args `mock`, `esp_port`, `lidar`, `lidar_port` |
| `config/robot.yaml` | parameters of the two nodes |
| `setup.py`, `package.xml` | executables; the firmware folder is also installed to `share/explorer_bringup/firmware/` |

Used from other packages: `src/explorer_description/urdf/explorer.urdf.xacro` (frames
`imu_link`, `laser_frame`), `src/explorer_description/config/ekf.yaml` ([[Odometry fusion]]),
`src/explorer_exploration/launch/bringup.launch.py` (includes `robot.launch.py` when `sim:=false`).

### Changes to the copied sketches
- rover_tests 2, 5, 6, 7: the variables `GYRO_BIAS_X/Y/Z` were renamed `GYRO_X/Y/Z_BIAS`. The
  SparkFun library `#define`s `GYRO_BIAS_Z`, so 5–7 did not compile as written.
- `icm20948_calibration.ino` = `icm20948_i2c.ino` without the stray text on its first lines.
- Otherwise identical to the originals below. All 11 sketches compile (core 3.3.12, no warnings).

## Outside the repo (originals, on the laptop)
| Path | What |
|------|------|
| `~/Downloads/rover_tests.zip` | the user's original test sketches |
| `~/snap/arduino/85/Arduino/icm20948_i2c/` | original IMU sketch (doesn't compile: stray text on lines 1–3) |
| `~/snap/arduino/85/Arduino/sketch_aug29c/` | original RSSI sniffer, logger, and the RSSI CSV logs of the field tests |
| `~/Documents/project_updatess/esp_rssi/` | earlier RSSI research; its `pi_rssi_logger.py` expects JSON and doesn't match the sniffer |
| `~/Arduino/libraries/SparkFun_9DoF_IMU_Breakout_-_ICM_20948_-_Arduino_Library/` | library for rover_tests 2, 5–7 (installed 2026-10-28, v1.3.2) |
| `~/.arduino15/` | arduino-cli and Arduino IDE 2 boards (esp32 3.3.12). The Arduino snap uses its own folder with core 2.0.14, too old for this code |

## Versions (git)
Branch `exp/hardware-esp32` on github.com/patnana-tarun/ros2_ws.
| Tag | State |
|-----|-------|
| `hw-esp32-v0` | first version of the ESP32 split, tested without hardware |
| `hw-esp32-v1` | + test tools, sketches in the repo, these docs, all checks passing |

Back to a version: `git checkout hw-esp32-v1 -- src/explorer_bringup` (just this package), or
`git checkout hw-esp32-v1` (everything, detached), then `colcon build --packages-select
explorer_bringup`. The old Pi-GPIO drivers: `git show f51e124:src/explorer_bringup/explorer_bringup/explorer_base.py`.
