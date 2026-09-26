---
tags: [robot]
source: src/explorer_description/urdf/explorer.urdf.xacro
---
# Robot model

A 6-wheel skid-steer chassis in the Kit4Curious style, with **rocker-bogie** suspension. On
each side a rigid *rocker* (side plates fixed to the top plate) carries one end wheel and a
pivot bolt. A free-swinging L-shaped *bogie* hangs from that bolt and carries the middle wheel
and the other end wheel. All 6 wheels are driven by BO geared DC motors.

**The bogie end is the front** (user, 2026-09-26), and the LiDAR sits over it. The idea is
that the bogie's two wheels meet a rock first and the pivot lets them climb it. The xacro
switch `bogie_leads` (default `true`) mirrors the chassis; `false` gives the rocker-first
layout. What each layout can climb in simulation is in [[Rock climbing]].

Frames follow REP-103: x forward, y left, z up. Units are metres, kg and rad. Package:
[[explorer_description]]. Simulation: [[Gazebo simulation]].

## Dimensions
| Quantity                 | Value                      | Source   |
|--------------------------|----------------------------|----------|
| Top plate                | 198 × 143 × 2.5 mm         | measured |
| Plate top above ground   | 130 mm                     | measured |
| Wheel                    | Ø 65 × 25 mm               | measured |
| Axles (front/mid/rear)   | +120 / 0 / −120 mm         | measured |
| Track (centre–centre)    | 176 mm                     | measured |
| Bogie pivot              | 95 mm high, 60 mm from the middle axle toward the front | measured / derived (90° L) |
| Bogie swing              | 43° front (end) wheel up, 28° middle wheel up (±5°) | measured from photos |
| base_link                | at axle height, 32.5 mm above ground | convention |
| LiDAR scan plane         | x = +79 mm, 180 mm above ground | assumed 50 mm LiDAR height |
| IMU (`imu_link`)         | robot centre, under the top plate, chip facing down (z down, y right; x forward assumed), 127.5 mm up | user: "centre, on the main base, facing down" |
| Raspberry Pi             | x = −66 mm, long side across the robot | assumed |

## Sensors (from the user, 2026-09-26)
| Sensor | Part | Mounting | Simulated as |
|--------|------|----------|--------------|
| LiDAR | YDLIDAR X2 | `laser_frame` | 360°, 7 Hz, 430 samples, 0.12–8 m, σ = 1 cm |
| IMU | MPU-9250 | `imu_link`, centre, facing down | 100 Hz gyro + accel with datasheet noise. Reads gravity as −9.8 on its z. Magnetometer not simulated |
| Encoders | LM393 slot sensors with slotted disks | the 4 corner wheels (front and rear), not the middle ones | Gazebo DiffDrive wheel odometry on `/wheel/odom` |

How they are fused: [[Odometry fusion]].

## Mass budget (all assumed)
| Part | Plate | Rocker ×2 | Bogie ×2 | Wheel ×6 | LiDAR | Pi | **Total** |
|------|-------|-----------|----------|----------|-------|----|-----------|
| g    | 105   | 70 each   | 105 each | 30 each  | 170   | 46 | **≈ 851** |

Other assumptions:
- BO motor body 65 × 18.5 × 22 mm.
- Wheel joint limits 0.078 N·m and 20.9 rad/s (200 RPM). The user's motor is rated 0.35 kg·cm (0.034 N·m) at 200 RPM, 3–12 V. The joint limit is the *peak* (stall) torque, assumed at about 0.8 kg·cm (typical for 200 RPM BO motors). With the rated 0.034 N·m as the limit, the robot could not turn on the spot at all ([[Gazebo simulation]]).
- LiDAR as a Ø 70 × 50 mm cylinder.
- Pi as 85 × 56 × 20 mm.

Inertias come from the solid box and cylinder formulas.

## Kinematic tree (16 links)
```
base_footprint
└── base_link                       fixed, z = +wheel_r
    ├── left_rocker                 fixed, y = +63.75 mm
    │   ├── left_rear_wheel         continuous
    │   └── left_bogie              revolute −43°…+28°, damping 0.05 (passive)
    │       ├── left_middle_wheel   continuous
    │       └── left_front_wheel    continuous
    ├── right_rocker …              mirror image
    ├── lidar_link ── laser_frame   fixed (laser_frame = scan frame_id)
    ├── imu_link                    fixed, roll 180° (facing down), massless (MPU-9250 breakout)
    └── pi_link                     fixed
```
