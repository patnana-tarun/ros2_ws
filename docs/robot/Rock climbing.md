---
tags: [robot]
source: src/explorer_description/urdf/explorer.urdf.xacro
---
# Rock climbing

What the [[Robot model]]'s rocker-bogie can drive over in simulation, and whether leading with
the bogie helps.

## Test (2026-09-26)
- A rounded rock (a cylinder lying across the path, height as listed) was placed 0.45 m ahead.
- The robot drove at it at 0.15 m/s for 9 s on flat ground in `empty.sdf`.
- "Crossed" means it travelled more than 0.8 m.
- "One side" is a 7 cm-wide rock under the left wheel track; "both tracks" is 40 cm wide.
- Wheel torque limit 0.078 N·m (assumed stall), friction μ = 1.0, effective track width 0.43 m
  ([[Gazebo simulation]]).

| Rock | Bogie first (current layout) | Rocker first |
|------|------------------------------|--------------|
| 3 cm, both tracks | crossed (pitch 9°) | – |
| 5 cm, both tracks | crossed (15°) | crossed (15°) |
| 6 cm, both tracks | stopped at the rock | stopped part-way up (18°) |
| 7 cm, both tracks | stopped at the rock | stopped part-way up (21°) |
| 5 cm, one side | crossed (roll 6°) | – |
| 6 cm, one side | crossed (roll 11°) | crossed (roll 12°) |
| 7 cm, one side | stopped at the rock | crossed (roll 16°) |
| 8 cm, one side | – | crossed (roll 35°) |

## Reading
- About **5 cm** (1.5 × wheel radius) is the limit for a rock under both tracks, in either
  direction.
- Leading with the bogie did **not** climb better. Rocker-first crossed one-sided rocks up to
  8 cm, bogie-first only up to 6 cm.
  - Likely reason: the rocker-end wheel is fixed rigidly to the chassis, so the bogie pair
    behind it pushes it up and over. A leading bogie wheel pivots away instead of being
    pushed into the rock.
  - This is simulation with an assumed stall torque. Check it on the real robot before
    deciding which end is the front.
- Every rock in the [[Cave world]] is taller than 26 cm, so the robot has to steer around
  them all. Nav2 treats them as obstacles.
