---
tags: [package]
path: src/explorer_bringup
build_type: ament_python
---
# explorer_bringup

Runs the **real robot**. It publishes the same topics and TF as the [[Gazebo simulation]], so
SLAM, Nav2 and [[explorer_exploration]] run unchanged. The hardware is listed in [[Robot model]].

```bash
ros2 launch explorer_exploration bringup.launch.py sim:=false rviz:=false   # everything, on the Pi
ros2 launch explorer_bringup robot.launch.py                                # robot only
ros2 launch explorer_bringup robot.launch.py lidar:=none                    # ESP32 sensors only
ros2 launch explorer_bringup robot.launch.py mock:=true                     # no hardware (test)
```

## Split: the Pi is the brain, the ESP32 is the controller
The Raspberry Pi 4 runs ROS 2 (SLAM, Nav2, exploration, the EKF, the mesh relay) and the X2
LiDAR. An ESP32 (DevKit, ESP32 Arduino core 3.x) runs everything with hard timing: motor PWM,
the four encoders, the speed loop, the IMU and a safety stop. They talk over USB serial. The
Pi's own GPIO isn't used.

```
/cmd_vel ─> esp32_bridge ──S,<left>,<right> (20 Hz)──> ESP32: PI speed loop ─> TB6612FNG ─> motors
                  <──T lines (50 Hz): 4 wheel travels, gyro, accel ──  encoders, ICM-20948
esp32_bridge ─> /wheel/odom, /imu, /joint_states ─> EKF ─> /odom + TF odom → base_footprint
x2_lidar ─> /scan ─> SLAM Toolbox ─> /map + TF map → odom
```

## Nodes
| Executable | Hardware | In → out |
|------------|----------|----------|
| `esp32_bridge` | ESP32 on USB serial (`esp_port`) | `/cmd_vel` (TwistStamped) → side speeds; telemetry → `/wheel/odom`, `/imu` (frame `imu_link`), `/joint_states` |
| `x2_lidar` | YDLIDAR X2 on USB serial (`lidar_port`) | → `/scan` (frame `laser_frame`), 360 beams of 1°, 7 Hz |

`robot.launch.py` also starts robot_state_publisher and the EKF ([[Odometry fusion]]).
`lidar:=ydlidar` uses the vendor `ydlidar_ros2_driver` instead, if it was built from source.
Parameters: `config/robot.yaml`. Both ports may also be pyserial URLs (`socket://host:port`).

## ESP32 firmware: `firmware/explorer_esp32/`
One Arduino sketch, one header per job, no libraries:

| File | Job |
|------|-----|
| `config.h` | every pin, constant and gain (the authoritative wiring) |
| `motors.h` | TB6612FNG: PWM 20 kHz, 8 bit, duty capped at 191 (~75 %: 9 V motors, 12.6 V pack) |
| `encoders.h` | 4 encoders, interrupt on A, direction from B (or from the command if single-channel) |
| `imu.h` | ICM-20948 register driver: ±250 °/s, ±2 g, DLPF ~50 Hz, 200 Hz sampling averaged per T line |
| `pilink.h` | the line protocol with the Pi (format documented at the top of the file) |
| `explorer_esp32.ino` | feed-forward + PI speed loop per side at 50 Hz, watchdog, telemetry |

- **Speed loop:** side speed = mean of its front and rear encoders, smoothed; duty =
  KF·target + KP·error + KI·∫error, integral clamped. Gains start from rover_tests 4.
- **IMU:** gyro bias is measured at every boot (robot still for 2 s; retried if it moves).
  The accelerometer's 6-face calibration is loaded from flash if `icm20948_i2c.ino` saved one.
  Data stay in the chip's axes; the URDF's `imu_joint` rotates them.
- **Safety:** motors stop 0.5 s after the last `S` command (3 s after a bench key), and stay
  disabled while `TICKS_PER_REV` is 0.
- **Integrity:** every line carries an NMEA-style XOR checksum; bad lines are dropped.
- **Later:** RSSI sniffing fits as one more header plus one more line type on the same link.

## How `esp32_bridge` fuses
- Side speeds from `/cmd_vel` use the **effective** track width (0.43 m, from simulation): a
  skid-steer's wheels slide sideways when it turns. Calibrate it: command a turn rate, read the
  real rate on `/imu`, scale `track_width` by commanded/actual.
- `/wheel/odom` carries vx (and vy = 0); the EKF takes yaw rate from the gyro.
- **Slip:** if the front and rear wheel of a side disagree by more than 30 %, vx goes out with
  variance 0.25 instead of 0.002, so the EKF leans on its prediction and the gyro.
- If the ESP32 restarts or the cable is pulled, the bridge reconnects and restarts its
  reference; it warns if the port is silent (wrong port, no firmware), has no IMU, or the drive
  is disabled.

## How `x2_lidar` works
The X2 needs no commands: powered, it spins and streams packets (header `AA 55`, sample count,
start/end angle, XOR checksum, distances in ¼ mm). The driver applies the X2's triangulation
angle correction, turns the clockwise angles into ROS's counter-clockwise ones, and bins each
turn into 360 fixed beams (nearest point per beam), so every scan has the same size for SLAM
Toolbox. Corrupt bytes are skipped by resyncing on the header. The adapter's DTR switches the
motor (`motor_dtr`).

## Wiring (ESP32 GPIO; from rover_tests)
| Signal | Pin |
|--------|-----|
| Left PWM / IN1 / IN2 (driver 1 A+B, driver 2 A) | 25 / 26 / 27 |
| Right PWM / IN1 / IN2 (driver 2 B, driver 3 A+B) | 33 / 14 / 13 |
| STBY, all three drivers (+10 kΩ to GND) | 4 |
| Encoder A / B: left front, left rear | 16 / 17, 18 / 19 |
| Encoder A / B: right front, right rear | 23 / 34, 35 / 32 (34, 35: 10 kΩ pull-up to 3.3 V) |
| ICM-20948 SDA / SCL (Qwiic, 3.3 V) | 21 / 22 |

## Bring-up on the hardware
1. **Measure** with the rover_tests sketches: `TICKS_PER_REV` (test 3), KP/KI (test 4). Put
   them in `config.h`.
2. **Flash:** Arduino IDE, open `explorer_esp32.ino`, board *ESP32 Dev Module*, upload. Or
   `arduino-cli compile --upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware/explorer_esp32`.
3. **Bench, wheels off the ground:** Serial Monitor 115200, Newline. Expect `# IMU: ICM-20948
   at 0x69`, the gyro bias, then T lines. Keys `w s a d x` drive each side at 0.15 m/s.
4. **On the Pi:** `ls -l /dev/serial/by-path/` gives a stable name per USB socket. Then
   `ros2 launch explorer_bringup robot.launch.py lidar:=none esp_port:=/dev/serial/by-path/...`.
   Turn the robot by hand counter-clockwise: `/odom` `twist.angular.z` must be **positive**. If
   it isn't, the IMU is mounted differently from the URDF's `imu_joint` (180°, 0, 90°); fix the rpy.
5. **LiDAR:** add `lidar_port:=...`; in RViz an object in front of the robot must show at 0°
   on `/scan`, otherwise set `angle_offset_deg`.
6. **Map:** `ros2 launch explorer_exploration bringup.launch.py sim:=false esp_port:=... lidar_port:=...`;
   `ros2 run explorer_exploration manual_drive` to drive by hand.

## Setup on the Pi
```bash
sudo apt install python3-serial ros-jazzy-robot-localization
sudo usermod -aG dialout $USER     # then log out and in
```

## Status
2026-10-28: firmware compiles (core 3.3.12, no warnings, both encoder modes). Without hardware:
mock launch gives `/odom` at 30 Hz following the command (0.15 m/s, 0.30 rad/s, yaw rate taken
through the IMU's URDF rotation); the bridge against a simulated ESP32 runs at ~49 Hz with all
checksums valid, flags slip and stops when `/cmd_vel` stops; `x2_lidar` against simulated X2
packets publishes 7.0 Hz scans with the right geometry and survives corrupt bytes; SLAM Toolbox
builds a map from it. **Not yet run on the robot** ([[Known limitations]]).

Before 2026-10-28 this package drove the motors from the Pi's GPIO (`explorer_base`) and read an
MPU-9250 over the Pi's I²C (`mpu9250_imu`); both are in git history.
