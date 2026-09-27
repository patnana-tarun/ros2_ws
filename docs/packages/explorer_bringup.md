---
tags: [package]
path: src/explorer_bringup
build_type: ament_python
---
# explorer_bringup

Runs the **real robot** on the Raspberry Pi. It publishes the same topics and TF as the
[[Gazebo simulation]], so SLAM, Nav2 and [[explorer_exploration]] run unchanged. The
hardware is listed in [[Robot model]].

```bash
ros2 launch explorer_exploration bringup.launch.py sim:=false rviz:=false   # everything, on the Pi
ros2 launch explorer_bringup robot.launch.py                                # robot only
ros2 launch explorer_bringup robot.launch.py mock:=true                     # no hardware (test)
```

## Nodes
| Executable | Hardware | In → out |
|------------|----------|----------|
| `explorer_base` | 3 × TB6612FNG (one per axle; A = left, B = right), LM393 20-slot encoders on the 4 corner wheels | `/cmd_vel` (TwistStamped) → motors; encoders → `/wheel/odom`, `/joint_states` |
| `mpu9250_imu` | MPU-9250 on I²C bus 1, address 0x68 | → `/imu` (frame `imu_link`, gyro bias removed) |

`robot.launch.py` also starts robot_state_publisher, the EKF ([[Odometry fusion]]) and
`ydlidar_ros2_driver` for the X2, if it is installed. That driver has to be built from
source (YDLidar-SDK + ydlidar_ros2_driver); it is not packaged for Jazzy.

## How `explorer_base` works
- **Kinematics:** skid-steer with the *effective* track width (0.43 m, calibrated in
  simulation). Recalibrate it on the robot: command a turn, measure it with the IMU, and
  scale by commanded/actual.
- **Speed control:** feed-forward (duty = speed / 0.68 m/s, the 200 RPM top speed) plus PI
  per side on encoder speed. A minimum duty of 0.25 gets the BO motors moving.
- **Encoders:** 20 slots = 10.2 mm of travel per slot, counted on rising edges through lgpio
  alerts. They are single-channel and can't sense direction, so each side takes its sign
  from the commanded direction. Speed is averaged over 0.25 s (at 0.2 m/s that is about 5
  slots, so it is coarse).
- **Safety:** motors stop if `/cmd_vel` is silent for 0.5 s, and the drivers go into
  standby on shutdown.

## Wiring
The GPIO pins are parameters in `config/robot.yaml` (BCM numbers). **The defaults are an
example; set them to the real wiring before the first run.**

Wiring every wheel separately would need 25 GPIOs, including the UART, SPI and ID-EEPROM
pins. The example instead shares each side's IN1/IN2/PWM between its three wheels (a
skid-steer drives a side's wheels alike) and the three STBY lines: 11 pins in all. The node
refuses a pin used for two *different* signals, and GPIO 2/3 (I²C).

| Signal | Example BCM pin |
|--------|-----------------|
| Left IN1 / IN2 / PWM (all three left channels A) | 5 / 6 / 12 |
| Right IN1 / IN2 / PWM (all three right channels B) | 23 / 24 / 13 |
| STBY (all three drivers) | 4 |
| Encoders: left front / left rear / right front / right rear | 17 / 27 / 22 / 16 |
| IMU SDA / SCL | 2 / 3 |

A motor that turns the wrong way: swap its wires, or add it to `invert`. A whole side can be
inverted even when its pins are shared.

## Setup on the Pi
```bash
sudo apt install python3-lgpio python3-smbus2 ros-jazzy-robot-localization
sudo raspi-config        # Interface Options -> I2C -> enable (Raspberry Pi OS),
                         # or add dtparam=i2c_arm=on to /boot/firmware/config.txt (Ubuntu)
sudo usermod -aG gpio,i2c,dialout $USER     # then log out and in
```

## Status
Tested with `mock:=true` only (2026-09-26): commanded 0.15 m/s and 0.3 rad/s came back
exactly on `/wheel/odom`, the EKF produced `/odom` and TF, the IMU's gravity read −9.81 on its
down-facing z, and the motors stopped 0.5 s after the last command. **Not yet run on the
Pi:** GPIO, I²C, PWM and the LiDAR driver are untested ([[Known limitations]]).
