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

## Results
- [[Comparisons]]: every design choice that was settled by comparing options, with charts (confirmed results only)
- Figures, one note per folder in `assets/` (each picture with a one-line meaning): [[Comparisons figures]], [[Robot figures]], [[Frontier exploration figures]], [[Navigation stack figures]], [[Baseline runs figures]], [[Planner comparison figures]], [[Planner follow-ups figures]], [[Tunnel tracking figures]], [[Run to 90 percent figures]], [[Full comparison figures]], [[Navigation fixes figures]], [[Stall ablation figures]], [[Reverse-out figures]], [[Tunnel-reverse figures]], [[Nav speed figures]], [[Rover MCP figures]]

## Packages
- [[my_mesh_interfaces]]: the custom mesh messages
- [[mesh_nodes]]: the relay node
- [[explorer_description]]: the robot model and Gazebo simulation
- [[explorer_exploration]]: autonomous frontier exploration with Nav2
- [[explorer_bringup]]: the real robot: Pi nodes, launch and ESP32 firmware

## Concepts
- [[Message envelope]] → [[PDR measurement]] → [[Run logging]]
- [[QoS design]]
- [[Relay rates]] (replaced the [[Map-in-flight throttle]])
- [[Topics]]: every topic, in one table
- [[Mesh network setup]]: IBSS + BATMAN-adv settings, node addresses, start/stop scripts
- [[Relay placement protocol]]: how to collect data for the relay-drop threshold
- [[Map freshness requirement]]: at most one map missed in a row (about 6 s), never more than two (about 9 s)
- [[Frontier exploration]]: TAD scoring and the gap filling
- [[Navigation stack]]: SLAM Toolbox + Nav2 tuned for this robot
- [[Tuning loop]]: how changes are tried and confirmed in simulation, with the `rover` MCP server
- [[Demo recording]]: chase camera in Gazebo, box-following RViz view, side-by-side backup video

## Hardware (the real robot)
- [[Hardware]]: start page: Pi 4 = brain, ESP32 = controller; wiring, bring-up, debugging, test tools

## Robot
- [[Robot model]]
- [[Gazebo simulation]]
- [[Cave world]]: procedural cave to test and train in
- [[Odometry fusion]]: encoders + IMU in an EKF
- [[Rock climbing]]: what the rocker-bogie can drive over

## Open issues
- [[Known limitations]]
- [[Discovery server not running]]: empty Gazebo world / nothing in RViz
- [[Nav2 not loaded]]: robot sits still, coordinator stuck at "waiting for Nav2"
- [[GUI crashes in VS Code terminal]]: Gazebo/RViz die at start, the launch shuts down
- [[Baseline runs 2026-10-08]]: 3 observed runs, problem evidence database (P01–P13)
- [[Relay field tests 2026-10-17]]: 3 walk tests of the Pi Zero 2 W repeater
- [[Gazebo multicast No such device]]: repeated multicast error, caused by the phone's USB tether
- [[Path tracking and stalls 2026-10-18]]: why the robot leaves the path, and the 7 Hz warning
- [[Planner comparison 2026-10-18]]: NavFn vs Smac Lattice A/B, 3 × 10 min pairs
- [[Planner follow-ups 2026-10-18]]: 4-arm follow-up; Smac not adopted, NavFn stays (branch `exp/planner-tuning`)
- [[Tunnel tracking 2026-10-18]]: NavFn + smoothing + MPPI tuning, GUI runs (branch `exp/tunnel-tracking`, verdict pending)
- [[Run to 90 percent 2026-10-18]]: same 3 setups run until 90 % or stuck (GUI); 4 of 6 trapped in dead ends
- [[Full comparison 2026-10-19]]: 3 setups × 3 GUI runs to 90 %; tuned drives straightest (p = 0.006), smooth explores fastest
- [[Navigation fixes 2026-10-19]]: root causes (open-area drift, unknown-space paths, spins); tracking fixed, stuck regression open
- [[Stall ablation 2026-10-20]]: one demo fix undone per variant; the 0.34 sim track drives both the accuracy gain and the hesitation
- [[Reverse-out 2026-10-20]]: back out instead of turning round; best tracking and least stuck so far (n = 2)
- [[Tunnel-reverse 2026-10-20]]: reverse only in tunnels, turn round in the open; wedged in tight passages until the planner used a bigger robot and a guarded back-out along the own track (then 2 of 3 runs to 90 %, none wedged)
- [[Nav speed 2026-10-21]]: full runs to 95 %: coverage ceiling 98.5 %; MPPI swing fix (az_max), no false "complete", heading-aware frontiers, explored-goal cancel; 95 % in 7.9–12.6 min in 3 of 3 runs (HEAD 9.7–11.5 min or stopped early); rotation and unknown-plan gates still fail (1 event per run; out-and-back U-turns)
- [[Receiver (external)]]

## Log
- [[2026-09-26]]
- [[2026-09-27]]
- [[2026-09-29]]
- [[2026-09-30]]
- [[2026-10-05]]
- [[2026-10-06]]
- [[2026-10-08]]
- [[2026-10-09]]
- [[2026-10-10]]
- [[2026-10-14]]
- [[2026-10-15]]
- [[2026-10-17]]
- [[2026-10-18]]
- [[2026-10-19]]
- [[2026-10-20]]
- [[2026-10-21]]
- [[2026-10-22]]
- [[2026-10-23]]
- [[2026-10-24]]
- [[2026-10-25]]
- [[2026-10-26]]
- [[2026-10-28]]

## Quick start
```bash
cd ~/ros2_ws && colcon build && source install/setup.bash
ros2 launch explorer_description explorer_gazebo.launch.py rviz:=true   # drive it yourself
ros2 launch explorer_exploration bringup.launch.py                       # or: explore the cave autonomously
ros2 launch mesh_nodes explorer_relay.launch.py use_sim_time:=true
```
