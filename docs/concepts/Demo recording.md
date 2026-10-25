---
tags: [concept]
---
# Demo recording

A backup video for the review panel, in case the live demo fails (user's request, 2026-10-24).
One launch runs the sim with two automatic camera views and records them side by side:

```bash
ros2 launch explorer_exploration demo_record.launch.py                  # sim + cameras + MP4
ros2 launch explorer_exploration demo_record.launch.py record:=false    # live demo, cameras only
ros2 launch explorer_exploration demo_record.launch.py box_x:=6.0 box_y:=6.0 glide_s:=0.0
ros2 launch explorer_exploration demo_record.launch.py spawn:=random              # new safe start each run
ros2 launch explorer_exploration demo_record.launch.py spawn:=random seed:=3      # repeat one
ros2 launch explorer_exploration demo_record.launch.py x:=9.0 y:=-1.5 yaw:=1.57   # chosen start
```

The video is written to `~/demo_recordings/demo_<date>_<time>.mp4`. Ctrl-C stops everything.
The navigation is `tunnel_reverse.launch.py` unchanged; the launch only adds `rviz:=false` and a
Gazebo layout file. The cameras follow the robot's pose only, so they work the same while
`manual_drive` is driving ([[explorer_exploration]]).

## Start position
`spawn_point` (2026-10-25) uses `config/cave_clearance.npz`: per 0.1 m cell, the distance to the
nearest wall, boulder or stalagmite, 0 where the cell is rock or not reachable from the rest of the
cave (made by `scripts/make_cave_clearance.py` from the generator field; the floor at every cell
with ≥ 0.3 m clearance is within 2 cm of z = 0, so the spawn height stays 0.02 m).
- `spawn:=random`: a cell with ≥ 0.6 m clearance (room to turn round; 1270 cells in all five
  chambers) and a random heading. The launch log prints it as `x:= y:= yaw:=` to repeat it.
- `x:= y:= yaw:=` (default 0, 0, 0): used as given with ≥ 0.3 m clearance, else moved to the
  nearest ≥ 0.6 m cell, with a log line saying why.
- Only `cave.sdf` is checked; another world takes x, y, yaw unchecked.

Any other sim launch takes the same start from the command line:
`ros2 launch explorer_exploration tunnel_reverse.launch.py $(ros2 run explorer_exploration spawn_point random)`
(or `spawn_point 9.0 -1.5 1.57`).

## The two views
| Window | Script | Behaviour |
|--------|--------|-----------|
| Gazebo | `demo_chase_cam` | Third-person camera 1.2 m behind and 0.6 m above the robot. Gazebo applies the follow offset in the robot's frame, so the offset is turned by (smoothed heading − robot heading); the smoothed heading catches up with a 1.5 s time constant, so a turn on the spot doesn't whip the camera round |
| RViz | `demo_view_box` | An imaginary box (4 × 4 m) around a TF frame `view_anchor`. The RViz view is centred on `view_anchor`. While the robot is inside the box, the view stays still. When it crosses the edge, the anchor glides in 1 s to where the robot was, and the box is drawn there again (yellow outline) |

`config/demo_gui.config` is Gazebo's default layout without the Entity tree and Component
inspector panel, so the 3D view fills its window. `rviz/demo_view.rviz` is Nav2's default view
with Target Frame `view_anchor`, scale 80 px/m, the robot model on, and no panels (open them from
RViz's Panels menu). Topics and frames: [[Topics]].

## Live HUD
`demo_hud` (2026-10-25) draws on a dark plate in the view's frame (`view_anchor`), so it moves with
the view and is in the recording:
- **Explored %**: the measure the experiments report (known map cells over the cave's true floor,
  84.4 m²). The map frame starts at the spawn pose, so map cells are moved by the spawn x, y, yaw
  first. Checked on a random start (10.9, −1.4): with the offset, 3.3 % of known cells fall off the
  floor (walls); without it, 59.7 %. Another world shows the mapped area in m² instead.
- **Time**: sim time from the robot's first move (it waits about 8 s for Nav2 at start).
- **95% at mm:ss** once coverage passes 95 %, and **Done in mm:ss** on `/exploration_complete`
  (the clock stops there). `hud:=false` turns it off.

The plate can go anywhere in the view: pick RViz's **Interact** tool (toolbar, or key `i`) and
drag the plate. It keeps that place relative to the view while the view follows the robot, and
where it was dropped is saved to `~/.ros/demo_hud_position.json` for the next start. The first
start (no file) puts it just above the box; `hud_x:= hud_y:=` (m from the view centre, x right,
y up) place it from the launch and override the saved place. With Interact on, a drag that does
not start on the plate turns the view, as with Move Camera. Delete the file to go back to the
default place. It is an interactive marker (server `/demo_hud`), the only way to move a marker
from inside RViz without an extra plugin.

## Recorder
`demo_recorder` waits for both windows, moves Gazebo to the left half and RViz to the right half
of the screen, and records the two screen areas into one 1920 × 1080 MP4 at 25 fps. It encodes
on the GPU (`h264_nvenc`), or with libx264 if NVENC does not work, so the sim keeps the CPU. The
file is a fragmented MP4, so a recording that was killed still plays. What it captures and
misses: [[Known limitations]].

## Running the pieces by hand
Start a sim first, with `rviz:=false` so only the demo RViz opens, then any of these in their own
terminals (or `demo_record.launch.py start_sim:=false x:= y:= yaw:=` for all of them; the HUD
needs the sim's start pose):

```bash
ros2 launch explorer_exploration tunnel_reverse.launch.py rviz:=false
ros2 run explorer_exploration demo_chase_cam --distance 1.2 --height 0.6 --yaw-tau 1.5
ros2 run explorer_exploration demo_view_box --ros-args -p use_sim_time:=true -p box_x:=4.0 -p box_y:=4.0
ros2 run explorer_exploration demo_hud --ros-args -p use_sim_time:=true -p spawn_x:=0.0 -p spawn_y:=0.0 -p spawn_yaw:=0.0
rviz2 -d install/explorer_exploration/share/explorer_exploration/rviz/demo_view.rviz --ros-args -p use_sim_time:=true
ros2 run explorer_exploration demo_recorder                       # --layout screen, --no-tile
```

Without the demo Gazebo layout, the Gazebo side panel takes about 40 % of the left half. Add
`gui_config:=$(ros2 pkg prefix explorer_exploration)/share/explorer_exploration/config/demo_gui.config`
to the sim launch to avoid it. `demo_chase_cam` uses gz-transport only (no ROS), so it needs
the sim's `GZ_PARTITION`.
