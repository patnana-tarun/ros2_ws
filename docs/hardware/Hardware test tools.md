---
tags: [robot]
---
# Hardware test tools

Four executables in `explorer_bringup`, for testing without the robot and for looking at the
real devices without ROS. Sources in `src/explorer_bringup/explorer_bringup/`.

## `hw_selftest`: does the software work?
```bash
ros2 run explorer_bringup hw_selftest              # ~40 s
ros2 run explorer_bringup hw_selftest --slam       # + SLAM Toolbox makes a map (~70 s)
ros2 run explorer_bringup hw_selftest --all        # + compiles the ESP32 firmware (arduino-cli)
```
Runs in its own ROS domain on localhost and free ports, so it never disturbs a running robot
or sim. Exit code 0 when nothing failed. What it checks:

| Check | Proves |
|-------|--------|
| firmware T-line format matches the bridge parser | the `send(...)` format in `explorer_esp32.ino` and `esp32_bridge.py` agree; a bad checksum is rejected |
| slip check flags a slipping wheel | the slip logic ([[esp32_bridge]]) |
| X2 packet decoding | `x2_lidar`'s parser on packets cut into random chunks, with garbage and a broken packet; angles within 0.05° |
| robot.launch.py comes up on the fake robot | the launch, bridge, EKF, LiDAR node start and connect |
| rates | `/wheel/odom`, `/imu`, `/joint_states` 40–60 Hz; `/odom` 25–35 Hz; `/scan` 6–8 Hz |
| `/imu` frame and gravity | frame `imu_link`, z ≈ −9.81 (chip facing down) |
| `/scan` geometry | ranges at 0, 45, 90, −90, 180° match the fake world within 8 cm (directions and the LiDAR's position) |
| TF | `odom → base_footprint → laser_frame` |
| EKF follows a command | 0.15 m/s and 0.30 rad/s come back on `/odom` |
| robot stops | wheel speed 0 within 1.5 s of the last `/cmd_vel` |
| SLAM (`--slam`) | SLAM Toolbox, with the project's `nav2_params.yaml`, maps the fake world |
| firmware (`--firmware`) | `explorer_esp32` compiles with no warnings |

**Limit:** the fake X2 encodes its packets with the same angle-correction formula that
`x2_lidar` decodes, so the test shows the two agree, not that the formula matches a real X2.
Bring-up step 5 ([[Hardware bring-up]]) is the real check.

## `fake_robot`: the whole robot, simulated
```bash
ros2 run explorer_bringup fake_robot          # ESP32 on socket://localhost:47001, X2 on :47002
ros2 launch explorer_exploration bringup.launch.py sim:=false rviz:=true \
    esp_port:=socket://localhost:47001 lidar_port:=socket://localhost:47002
```
A simulated ESP32 (same protocol, watchdog, IMU in chip axes) and X2 (real packet format,
ray-cast) in a 9 × 6 m world: two rooms joined by a doorway, a box and a pillar. The real nodes
connect to it with pyserial `socket://` URLs, so everything above the serial port runs as on
the robot. `--slip` makes the left rear wheel spin 50 % fast; `--no-imu` reports no IMU.
On 2026-10-28 the full stack (SLAM, Nav2, exploration) explored it on its own: through the
doorway, 50 of the 54 m² mapped in 150 s.

## `esp32_check`: what is the ESP32 sending?
```bash
ros2 run explorer_bringup esp32_check /dev/ttyUSB0                   # watch
ros2 run explorer_bringup esp32_check /dev/ttyUSB0 --drive 0.1 0.1   # also drive each side at 0.1 m/s
```
Twice a second: lines/s, bad checksums, each wheel's speed, duties, gyro z, |accel| (≈ 9.81),
and the flags in words (`IMU`/`NO-IMU`, `drive`/`DRIVE-OFF`, `WATCHDOG`). ESP32 messages are
printed as they come. Sends `S,0,0` on exit. Doesn't reset the ESP32.

## `x2_check`: what is the LiDAR sending?
```bash
ros2 run explorer_bringup x2_check /dev/ttyUSB1
```
Once a second: bytes/s, packets/s, turns/s (expect ~7), points per turn (~430), the range at
the X2's own 0/90/180/270° (clockwise from its zero mark) and the nearest object. Says what is
wrong if nothing valid arrives.

All four accept a device or a pyserial URL. Stop `robot.launch.py` before using a checker on
the same port: only one program can hold it.
