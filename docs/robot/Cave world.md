---
tags: [robot]
source: src/explorer_description/scripts/generate_cave.py
---
# Cave world

A procedurally generated cave to test and train the explorer in. It is scaled to the
[[Robot model]] and loaded by the launch in [[Gazebo simulation]].

![[cave_views.jpg]]
*Top row: the big hall (C) and a tunnel, from inside the closed cave. Bottom row: the closed
cave from above (the ceiling is invisible from outside), and the roofless `cave_open` world.*

## Worlds
| World            | Roof | Light | Use |
|------------------|------|-------|-----|
| `cave.sdf`       | yes  | 15 warm point lamps, dark ambient, black background | the real test. Inside it is fully enclosed |
| `cave_open.sdf`  | no, walls cut at 0.5 m | sun with shadows | watching the robot from above while training |

Both have the same layout and collision. The ceiling faces only downwards, so it is solid
from inside but see-through from above. That way the Gazebo GUI can watch the robot in
`cave.sdf` too.

## Layout
About 23 × 16.5 m. Six chambers (A–F, 2–6 m across) are joined by nine winding tunnels
0.7–1.0 m wide. The robot spawns at (0, 0), the centre of chamber A.
- **Loops:** A–B–C–D and B–C–E, for SLAM loop closure
- **Dead ends:** off A (west), off D (south-west), and chamber F
- **Heights:** ceiling about 0.45–0.8 m in tunnels and up to 1.4 m in chambers
- **Obstacles:** 37 boulders and stalagmites, all inside the chambers.
  - Every one is at least 0.26 m tall, i.e. at LiDAR level, as the user asked for testing.
    Stalagmites stay column-shaped up to 0.24 m, so the scan plane (0.18 m) cuts each rock
    at 65–100 % (median 92 %) of its base width.
  - Earlier versions had rocks lower than the scan plane, which the LiDAR couldn't see (the
    robot got stuck on a 7.8 cm boulder). They also placed 4 rocks inside tunnels, one of
    which blocked the A→B tunnel.
  - Stalactites are well above the robot and visual only.
- **Puddles:** 6 dark, glossy patches on the floor, visual only

The generator refuses a layout in which any chamber can't be reached from the spawn by a
0.32 m-wide robot.

## How it is built
1. **Signed distance field.** A 2D field over the whole area, negative in open space. It is
   built from the hand-placed chambers (wobbly ellipses) and tunnels (Catmull-Rom centre lines
   with meander and width noise), smoothly blended together and roughened with noise.
2. **Two height fields** come from that field, on a 5 cm grid:
   - floor/wall: gravel-bumpy floor, then a wall rising with √distance
   - ceiling: a dome over open space that comes down to meet the walls

   Both are lightly blurred. Each grid cell is split along the diagonal with the smaller
   height change, so steep walls don't render as a sawtooth.
3. **Meshes** (OBJ): floor, walls, ceiling, formations, puddles. UVs use a per-face triplanar
   projection.
4. **Textures** (1024², tiling, generated): layered limestone rock with iron stains and faint
   cracks, and gravel made of rounded pebbles in dirt. Each has a normal map and uses the PBR
   material.

## Collision vs. what the LiDAR sees
- **Floor:** a flat plane at z = 0. The visual floor is within ±1.5 cm of it.
- **Walls:** near-vertical, standing where the visual wall reaches 0.12 m. When collision
  followed the visual slope, the rocker-bogie climbed the wall foot at full speed and flipped.
- **Boulders and stalagmites:** collide using their own meshes.
- **LiDAR:** the scan plane is at about 0.18 m and hits the *visual* wall, a few cm behind the
  collision wall.

## Build and variants
`colcon build` runs the generator (about 5 s) into `build/explorer_description/cave/` and
installs the output to `share/explorer_description/{models,worlds}`. The meshes and textures total
about 29 MB, so they are not committed. The launch file adds both folders to
`GZ_SIM_RESOURCE_PATH`, so `world:=cave.sdf` works by name.

To get the same layout with different rock detail, run the generator with another seed:
```bash
ros2 run explorer_description generate_cave.py --out /tmp/cave42 --seed 42
GZ_SIM_RESOURCE_PATH=/tmp/cave42/models:$GZ_SIM_RESOURCE_PATH \
  ros2 launch explorer_description explorer_gazebo.launch.py world:=/tmp/cave42/worlds/cave.sdf
```
Only the noise changes with the seed. The chambers and tunnels are fixed in the `CHAMBERS` and
`TUNNELS` tables at the top of the script. Edit those to change the layout.

Limitations are in [[Known limitations]].
