---
tags: [package]
path: src/explorer_bringup
build_type: ament_python
---
# explorer_bringup

Runs the **real robot**: the Pi-side nodes, the launch, and the ESP32 firmware. It publishes
the same topics and TF as the [[Gazebo simulation]], so SLAM, Nav2 and [[explorer_exploration]]
run unchanged. Everything about the hardware is in the [[Hardware]] folder; start there.

```bash
ros2 launch explorer_exploration bringup.launch.py sim:=false esp_port:=... lidar_port:=...   # everything
ros2 launch explorer_bringup robot.launch.py esp_port:=... lidar_port:=...   # robot only (lidar:=x2|ydlidar|none)
ros2 launch explorer_bringup robot.launch.py mock:=true                     # no hardware at all
ros2 run explorer_bringup hw_selftest --all                                 # test the software
```

| Executable | Note |
|------------|------|
| `esp32_bridge` | [[esp32_bridge]]: ESP32 ↔ `/cmd_vel`, `/wheel/odom`, `/imu`, `/joint_states` |
| `x2_lidar` | [[x2_lidar]]: YDLIDAR X2 → `/scan` |
| `fake_robot`, `esp32_check`, `x2_check`, `hw_selftest` | [[Hardware test tools]] |

`robot.launch.py` also starts robot_state_publisher and the EKF ([[Odometry fusion]]).
Firmware: [[ESP32 firmware]]. Files: [[Hardware files]]. How it fits together:
[[Hardware architecture]].
