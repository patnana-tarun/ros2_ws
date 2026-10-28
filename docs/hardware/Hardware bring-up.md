---
tags: [robot]
---
# Hardware bring-up

From a bare robot to a map, one step at a time. **Do the steps in order** and don't go on until a
step shows what it should; when it doesn't, go to [[Hardware debugging]]. Wheels off the
ground (robot on a box) for every step that moves motors, until step 6.

## 0. Software on the Pi (once)
```bash
sudo apt install python3-serial ros-jazzy-robot-localization ros-jazzy-slam-toolbox ros-jazzy-navigation2
sudo usermod -aG dialout $USER                      # serial ports without sudo; log out and in
cd ~/ros2_ws && git fetch && git checkout exp/hardware-esp32
colcon build && source install/setup.bash
ros2 run explorer_bringup hw_selftest              # must end with "0 failed"
```
The Arduino tools are needed only where you flash the ESP32 (laptop or Pi): Arduino IDE 2 or
`arduino-cli`, with the *esp32* boards package 3.x (Boards Manager, URL
`https://espressif.github.io/arduino-esp32/package_esp32_index.json`) and, for rover_tests 2
and 5–7 only, the library "SparkFun 9DoF IMU Breakout - ICM 20948".

## 1. Measure with the test sketches
`src/explorer_bringup/firmware/rover_tests/`, each at 115200 baud in the Serial Monitor (Newline):

| Sketch | Do | Write down |
|--------|----|------------|
| `1_motor_test` | `q` then `e`: each side alone forward; `w`, `s`, `a`, `d` | a side turning backwards → `INVERT_LEFT/RIGHT` |
| `3_encoder_test` | turn each wheel forward by hand: all four counts must rise; then `m`, exactly 10 turns of the left front wheel, `m` | `TICKS_PER_REV`; a falling count → its `ENC_SIGN` |
| `4_motor_encoder_pid` | set `TICKS_PER_REV` in it first; `w` at 0.15 m/s; tune with `k l i o` until "meas" follows "tgt" without swinging | `KP`, `KI` |
| `2_imu_calibration` (optional) | `c` with the robot still | gyro noise should be < 0.5 °/s |

Optional, for the accelerometer: flash `firmware/icm20948_calibration`, send `a`, lay the
robot (or the board) on each of its 6 faces; it saves the calibration to flash, where the
main firmware finds it.

## 2. Flash the controller
Put the numbers into `firmware/explorer_esp32/config.h`, then flash `explorer_esp32`
([[ESP32 firmware]], "Build and flash"). In the Serial Monitor, after a reset, **robot still**:
```
# explorer_esp32 starting - keep the robot still
# IMU: ICM-20948 at 0x69, accel calibration not done (optional: icm20948_i2c.ino 'a')
# gyro bias 0.412 -0.233 0.087 deg/s
# ready
T,2412,0,0,0,0,0.00003,-0.00010,0.00002,0.150,-0.090,-9.795,0,0,3*..
```
Flags `3` = IMU + drive. `1` means `TICKS_PER_REV` is still 0.

## 3. Bench test the controller (Serial Monitor)
Type `w`: both sides forward at 0.15 m/s; the four travel fields of `T` (the four numbers after
`ms`) rise by about 3000 µm per line (0.15 m/s × 20 ms) and the duties settle. `a`: left back,
right forward. `x`: stop. With no key for 3 s it stops by itself and the flags show `+4`.
Turning the robot by hand counter-clockwise (seen from above): `gz` (the third number after
the travels) goes **negative** — the chip faces down, so its z points down (step 4 checks
this properly). Field list: [[Serial protocol]].

## 4. On the Pi: robot without LiDAR
Close the Serial Monitor. Find the stable port names:
```bash
ls -l /dev/serial/by-path/        # one entry per USB socket; plug one device at a time to tell them apart
ros2 run explorer_bringup esp32_check /dev/serial/by-path/<ESP32>     # ~50 lines/s, bad 0, IMU drive
ros2 launch explorer_bringup robot.launch.py lidar:=none esp_port:=/dev/serial/by-path/<ESP32>
```
In a second terminal:
```bash
ros2 topic hz /wheel/odom          # ~50
ros2 topic hz /odom                # ~30 (the EKF)
ros2 topic echo /odom --field twist.twist.angular.z    # turn the robot by hand counter-clockwise
```
**`angular.z` must be positive while turning counter-clockwise.** If it is negative, the
ICM-20948 is mounted differently from the URDF: fix `imu_joint`'s `rpy` in
`src/explorer_description/urdf/explorer.urdf.xacro` (today `${pi} 0 ${pi/2}` = chip facing
down, x to the left), rebuild, repeat. Then drive:
`ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped "{twist: {linear: {x: 0.1}}}"`
→ `/odom` `linear.x` ≈ 0.1; Ctrl-C → the robot stops within 0.5 s.

## 5. The LiDAR
```bash
ros2 run explorer_bringup x2_check /dev/serial/by-path/<X2>   # ~7 turns/s, ~430 points/turn
ros2 launch explorer_bringup robot.launch.py esp_port:=... lidar_port:=/dev/serial/by-path/<X2>
rviz2      # Fixed Frame base_footprint, add LaserScan /scan, add RobotModel
```
Hold a box 0.5 m **in front** of the robot. In RViz it must be in front (+x, red axis). If it
appears at some angle θ (counter-clockwise positive), set `angle_offset_deg` in
`config/robot.yaml` to −θ, rebuild, check again. If the box appears mirrored (left ↔ right),
flip `inverted`. If the X2 doesn't spin: `motor_dtr: false`.

## 6. Track width (on the floor)
The bridge turns `/cmd_vel` into side speeds with the effective track width (0.43 m, from
simulation). Command a turn on the spot and compare with the gyro:
```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped "{twist: {angular: {z: 0.5}}}"
ros2 topic echo /imu --field angular_velocity.z      # chip faces down: the robot's rate is −z
```
New `track_width` = 0.43 × 0.5 / (measured rate). Put it in `config/robot.yaml`, rebuild.

## 7. A map
```bash
ros2 launch explorer_exploration bringup.launch.py sim:=false rviz:=false \
    esp_port:=/dev/serial/by-path/<ESP32> lidar_port:=/dev/serial/by-path/<X2>
ros2 run explorer_exploration manual_drive          # optional: drive by hand (pauses exploration)
```
On a laptop on the same network (same `ROS_DOMAIN_ID`, discovery server as in
[[Mesh network setup]]): `rviz2` with Fixed Frame `map`, `/map`, `/scan`. Exploration starts
by itself, as in simulation ([[Frontier exploration]]). Save a map with
`ros2 run nav2_map_server map_saver_cli -f ~/map_$(date +%F)`.
