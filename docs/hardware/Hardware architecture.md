---
tags: [robot]
---
# Hardware architecture

**The Raspberry Pi 4 is the brain; the ESP32 is the controller** (the user's decision,
2026-10-28). The Pi runs ROS 2: SLAM, Nav2, exploration, the EKF, the mesh relay, and the
LiDAR driver. The ESP32 does everything that needs hard timing: motor PWM, encoder counting,
the speed loop, IMU sampling, and the safety stop. They are joined by one USB cable. The Pi's
own GPIO pins are not used.

```mermaid
flowchart LR
  subgraph Pi["Raspberry Pi 4 (ROS 2 Jazzy)"]
    Nav["Nav2 + exploration"] -- "/cmd_vel" --> Br[esp32_bridge]
    Br -- "/wheel/odom, /imu" --> EKF[robot_localization EKF]
    Br -- "/joint_states" --> RSP[robot_state_publisher]
    EKF -- "/odom + TF odom→base_footprint" --> SLAM[SLAM Toolbox]
    X2N[x2_lidar] -- "/scan" --> SLAM
    SLAM -- "/map + TF map→odom" --> Nav
  end
  subgraph ESP["ESP32 DevKit"]
    Loop["PI speed loop, 50 Hz"] --> Drv["3× TB6612FNG → 6 motors"]
    Enc["4 wheel encoders"] --> Loop
    IMU["ICM-20948, 200 Hz"]
  end
  Br -- "USB serial: S,left,right at 20 Hz" --> Loop
  Loop -- "T lines at 50 Hz: wheel travel, gyro, accel" --> Br
  X2["YDLIDAR X2"] -- "USB serial, 115200" --> X2N
```

## Why this split
- **Timing.** On the Pi, Python drove the PWM by software and counted encoder pulses in
  callbacks; with SLAM and Nav2 loading the CPU, both jitter and pulses get missed. The ESP32
  has hardware PWM (LEDC) and dedicated interrupts, and nothing else to do.
- **Safety.** If the Pi stalls, crashes or the cable comes out, the ESP32 stops the motors
  itself 0.5 s after the last command.
- **One ROS interface.** The bridge publishes the same topics as the Gazebo simulation
  ([[Topics]]), so SLAM, Nav2 and exploration run on the robot without changes.
- **Fusion stays in ROS.** The ESP32 sends raw measurements (wheel travel, gyro, accel), not a
  pose. The EKF on the Pi fuses them ([[Odometry fusion]]), so the fusion can be tuned
  without reflashing, and the same EKF config serves the simulation.

## Who does what
| Job | Where | Rate |
|-----|-------|------|
| Motor PWM, 20 kHz | ESP32 ([[ESP32 firmware]]) | continuous |
| Speed loop per side (feed-forward + PI) | ESP32 | 50 Hz |
| Encoder counting (interrupts) | ESP32 | every pulse |
| IMU sampling, averaged per report | ESP32 | 200 Hz in, 50 Hz out |
| Watchdog stop | ESP32 | 0.5 s after the last command |
| `/cmd_vel` → side speeds (skid-steer kinematics) | Pi, [[esp32_bridge]] | 20 Hz to the ESP32 |
| Wheel odometry, slip check, `/imu`, `/joint_states` | Pi, [[esp32_bridge]] | 50 Hz |
| Fusion: `/odom`, TF `odom → base_footprint` | Pi, EKF | 30 Hz |
| LiDAR packets → `/scan` | Pi, [[x2_lidar]] | 7 Hz |
| SLAM, Nav2, exploration, mesh relay | Pi | as in simulation |

Kinematics (the effective track width) live on the Pi; wheel size, encoder resolution and
the speed-loop gains live on the ESP32. Each number is set in exactly one place.

## Before 2026-10-28
The first design drove the motors from the Pi's GPIO (`explorer_base`) and read an MPU-9250
on the Pi's I²C (`mpu9250_imu`). Both were replaced; they are in git history
([[Hardware files]]). The sensor parts are listed in [[Robot model]].
