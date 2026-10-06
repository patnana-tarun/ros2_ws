---
tags: [issue]
---
# Nav2 not loaded

**Symptom.** The robot sits still. Gazebo, SLAM, RViz and TAD all run, the map grows and TAD
publishes `/best_goal`, but the coordinator never logs `Sending goal`. It stays at
`waiting for Nav2...` and uses ~45 % CPU.

**Diagnosis (2026-09-30).**
- `ros2 action info /navigate_to_pose` showed 5 clients and **0 servers**.
- `/cmd_vel` had no publisher.
- `/nav2_container` was running but `list_nodes` returned an empty list, and `launch.log` had
  no `Loaded node` lines.

**Cause.** Nav2 ran in a component container (`use_composition` defaults to True). The launch
process loads each Nav2 node by calling the container's `load_node` service. In Fast DDS
discovery-server mode ([[Discovery server not running]]) that call missed the container during
startup and gave up silently, so the container stayed empty. The same stack loaded Nav2 fine
without the discovery server.

**Fix.** `bringup.launch.py` now passes `use_composition: False`. Each Nav2 server runs as its own
process, with no service call at startup.

**Verified 2026-09-30,** headless, without the discovery server: `/bt_navigator` served
`/navigate_to_pose`, `/cmd_vel` ran at 20 Hz, and the first goal was reached in 25 s. Not yet
verified in discovery-server mode.
