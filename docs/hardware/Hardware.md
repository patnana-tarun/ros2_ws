---
tags: [moc]
---
# Hardware

Start page for the **real robot**: the Raspberry Pi 4, the ESP32 controller, the sensors, and
the code that joins them to the ROS stack. Everything else in this vault is about the
simulation and the mesh relay; this folder is only about the hardware.

**Goal now:** sensors + LiDAR → SLAM → a map, driven by hand (`mapping.launch.py`). Nav2 and
autonomous exploration come later.

**Status (2026-10-28):** code complete and tested without hardware (all checks pass; a
hand-driven route on the simulated robot gives a clean map). Not yet run on the robot. Open items are in
[[Known limitations]] (#16).

## Read in this order
1. [[Hardware architecture]]: what runs where, and why (Pi = brain, ESP32 = controller)
2. [[Wiring]]: every pin and connection
3. [[Hardware bring-up]]: from flashing the ESP32 to a map, step by step, with what to expect
4. [[Hardware debugging]]: symptom → cause → check → fix
5. [[Hardware test tools]]: the self-test, the fake robot, and the port checkers

Reference: [[ESP32 firmware]], [[Serial protocol]], [[esp32_bridge]], [[x2_lidar]],
[[Odometry fusion]], [[Hardware files]] (where every file is, and how to restore a version),
[[RSSI merge plan]] (next step, not started).

## The five commands
```bash
ros2 run explorer_bringup hw_selftest --all                 # does the software still work? (~2 min)
ros2 run explorer_bringup esp32_check /dev/ttyUSB0          # what is the ESP32 sending? (no ROS)
ros2 run explorer_bringup x2_check /dev/ttyUSB1             # what is the LiDAR sending? (no ROS)
ros2 launch explorer_bringup robot.launch.py esp_port:=... lidar_port:=...      # robot + LiDAR, no map
ros2 launch explorer_bringup mapping.launch.py rviz:=true esp_port:=... lidar_port:=...   # + SLAM: drive by hand, map builds
```

## For another person or AI assistant picking this up
- Workspace: `~/ros2_ws` (ROS 2 Jazzy, colcon). Branch `exp/hardware-esp32` on
  github.com/patnana-tarun/ros2_ws; tags `hw-esp32-v0` (first version) and `hw-esp32-v1`
  (this documented, tested version). Rules for the repo and this vault: `CLAUDE.md` at the
  workspace root.
- All hardware code is in `src/explorer_bringup/` ([[Hardware files]] lists each file).
- **The protocol is defined in four places that must agree:** `firmware/explorer_esp32/pilink.h`
  and the `send(...)` in `explorer_esp32.ino` (ESP32 side), `esp32_bridge.py` (Pi side),
  `fake_robot.py` (test double). `hw_selftest` reads the format string from the `.ino` and
  checks the bridge parses it, so run it after any protocol change ([[Serial protocol]]).
- `src/explorer_description/config/ekf.yaml` is shared with the simulation: change real-robot
  EKF behaviour in `robot.launch.py` (as with `predict_to_current_time`), not in the YAML.
- After editing anything under `src/`, rebuild: `colcon build --packages-select explorer_bringup`
  (no symlink install; the old copy runs otherwise), then `source install/setup.bash`.
- Verify before claiming a fix: `hw_selftest --all` must end with `0 failed`.
