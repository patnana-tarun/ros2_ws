---
tags: [moc]
---
# Home

ROS 2 Jazzy workspace for the **explorer robot**. The robot runs SLAM and sends its map and
transforms over a lossy BATMAN-adv mesh to a receiver robot.

```
Explorer (this repo)                                                  Receiver (external)
LiDAR ─/scan─► SLAM ─/map─┐
drive ─/odom,/tf──────────┴─► explorer_relay_node ─/mesh/*─ BATMAN-adv ─► tf_rolling_metrics_node
```

## Packages
- [[my_mesh_interfaces]]: the custom mesh messages
- [[mesh_nodes]]: the relay node
- [[explorer_description]]: the robot model and Gazebo simulation

## Concepts
- [[Message envelope]] → [[PDR measurement]]
- [[QoS design]]
- [[Map-in-flight throttle]]
- [[Topics]]: every topic, in one table

## Robot
- [[Robot model]]
- [[Gazebo simulation]]

## Open issues
- [[Known limitations]]
- [[Receiver (external)]]

## Log
- [[2026-09-26]]

## Quick start
```bash
cd ~/ros2_ws && colcon build && source install/setup.bash
ros2 launch explorer_description explorer_gazebo.launch.py rviz:=true
ros2 launch mesh_nodes explorer_relay.launch.py use_sim_time:=true
```
