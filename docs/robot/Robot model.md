---
tags: [robot]
source: src/explorer_description/urdf/explorer.urdf.xacro
---
# Robot model

A 6-wheel skid-steer chassis in the Kit4Curious style, with **rocker-bogie** suspension. On
each side a rigid *rocker* (side plates fixed to the top plate) carries the front wheel and a
pivot bolt. A free-swinging L-shaped *bogie* hangs from that bolt and carries the middle and
rear wheels. All 6 wheels are driven by BO geared DC motors.

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
| Bogie pivot              | 95 mm high, 60 mm behind the middle axle | measured / derived (90° L) |
| Bogie swing              | 28° front-up, 43° rear-up (±5°) | measured from photos |
| base_link                | at axle height, 32.5 mm above ground | convention |
| LiDAR scan plane         | x = +79 mm, 180 mm above ground | assumed 50 mm LiDAR height |
| Raspberry Pi             | x = −66 mm, long side across the robot | assumed |

## Mass budget (all assumed)
| Part | Plate | Rocker ×2 | Bogie ×2 | Wheel ×6 | LiDAR | Pi | **Total** |
|------|-------|-----------|----------|----------|-------|----|-----------|
| g    | 105   | 70 each   | 105 each | 30 each  | 170   | 46 | **≈ 851** |

Other assumptions:
- BO motor body 65 × 18.5 × 22 mm.
- Wheel joint limits 0.08 N·m and 20.9 rad/s (200 RPM).
- LiDAR as a Ø 70 × 50 mm cylinder.
- Pi as 85 × 56 × 20 mm.

Inertias come from the solid box and cylinder formulas.

## Kinematic tree (15 links)
```
base_footprint
└── base_link                       fixed, z = +wheel_r
    ├── left_rocker                 fixed, y = +63.75 mm
    │   ├── left_front_wheel        continuous
    │   └── left_bogie              revolute −28°…+43°, damping 0.05 (passive)
    │       ├── left_middle_wheel   continuous
    │       └── left_rear_wheel     continuous
    ├── right_rocker …              mirror image
    ├── lidar_link ── laser_frame   fixed (laser_frame = scan frame_id)
    └── pi_link                     fixed
```
