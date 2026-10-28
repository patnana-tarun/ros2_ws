---
tags: [issue]
---
# Hardware debugging

## Method
1. **Is the software fine?** `ros2 run explorer_bringup hw_selftest` (40 s). If it fails, the
   fault is in the code or the build, not the hardware: rebuild (`colcon build
   --packages-select explorer_bringup`), or return to a tagged version ([[Hardware files]]).
2. **Is the device fine, without ROS?** Stop the launch, then `esp32_check` / `x2_check` on
   the port ([[Hardware test tools]]). Or the Arduino Serial Monitor for the ESP32.
3. **Is the link fine?** The node logs: `esp32_bridge` and `x2_lidar` warn every 5 s about
   what is missing. `ros2 topic hz` on each topic in the chain:
   `/wheel/odom` 50 → `/odom` 30 → `/scan` 7 → `/map` every 3 s.
4. Change one thing at a time, and check again from the step that failed.

Logs: the launch terminal; `~/.ros/log/<date-time>/`; `hw_selftest` writes `/tmp/hw_selftest_*.log`.

## Symptoms
| Symptom | Likely cause | Check | Fix |
|---------|--------------|-------|-----|
| `cannot open /dev/ttyUSB0` | wrong name, no permission, port busy | `ls -l /dev/serial/by-path/`; `groups` shows `dialout`? | right name; `sudo usermod -aG dialout $USER` and log in again; close the Serial Monitor / other launch |
| bridge: "no telemetry ... for 5 s" | port is the LiDAR's, firmware not flashed, wrong baud, ESP32 still calibrating | `esp32_check` on the port; Serial Monitor shows `T` lines? | swap `esp_port`/`lidar_port`; flash; `BAUD` = `baud` |
| `x2_check`: "bytes but no valid packets" | it's the ESP32's port, or wrong baud | does it print ESP32 text in a Serial Monitor? | swap ports |
| `x2_check`: "no bytes" | motor off, no power | does the X2 spin? | `--no-dtr` / `motor_dtr: false`; another USB port or a powered hub |
| ESP32 resets when motors start (`# explorer_esp32 starting` again) | motor noise or a supply dip on the ESP32 | Serial Monitor while driving | ESP32 from the Pi's USB only, common ground, capacitors on VM ([[Wiring]]) |
| `# IMU: no ICM-20948 at 0x69/0x68`, flags without 1 | wiring, 5 V, loose Qwiic | `firmware/icm20948_calibration` prints the bus lines and an I²C scan | SDA 21, SCL 22, 3.3 V |
| "drive disabled", flags without 2, motors never move | `TICKS_PER_REV` = 0 | boot message | set it in `config.h`, reflash |
| one side doesn't move | its PWM/IN wires, driver STBY, or a fuse | `1_motor_test` `q` / `e` | wiring; `STBY` on GPIO 4 |
| a side runs backwards | motor polarity | `1_motor_test` | `INVERT_LEFT/RIGHT` |
| a side runs away to full speed | its encoders count backwards (positive feedback) | `esp32_check`: wheel speeds negative while going forward? | flip that wheel's `ENC_SIGN` |
| wheel speed 0 although wheels turn | encoder not counting; GPIO 34/35 without pull-up | `3_encoder_test` | 10 kΩ to 3.3 V on 34 and 35 |
| speed swings around the target | `KP`/`KI` too high | `esp32_check --drive 0.15 0.15` | lower them (rover_tests 4) |
| robot stops every 0.5 s / jerks | `S` commands not arriving often | flags `+4` in `esp32_check`? bridge log | Pi overloaded, cable; `cmd_rate` |
| map rotates or smears when turning | IMU yaw sign wrong, or track width far off | bring-up step 4 and 6 | `imu_joint` rpy; `track_width` |
| obstacles appear in the wrong direction | `angle_offset_deg` / `inverted` | bring-up step 5 | calibrate |
| `/odom` at 20 Hz instead of 30 | `predict_to_current_time` missing | `robot.launch.py` | it is set there for the robot ([[Odometry fusion]]) |
| SLAM: "Message Filter dropping message" | TF `odom → base_footprint` missing or late | `ros2 run tf2_ros tf2_echo odom base_footprint` | EKF running? `/wheel/odom` and `/imu` arriving? |
| no `/map` | SLAM not activated (lifecycle), no `/scan` | `ros2 lifecycle get /slam_toolbox` | the full bringup activates it; standalone: `ros2 lifecycle set /slam_toolbox configure`, then `activate` |
| launch can't find nodes / old behaviour after an edit | not rebuilt / not sourced | `ros2 pkg executables explorer_bringup` | `colcon build --packages-select explorer_bringup && source install/setup.bash` |
| nodes on the laptop and Pi don't see each other | discovery server / domain | [[Discovery server not running]] | as in the mesh setup |
