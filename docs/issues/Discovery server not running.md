---
tags: [issue]
---
# Discovery server not running

**Symptom.** The Gazebo world opens empty and RViz shows nothing. The spawner (`ros_gz_sim create`)
prints `Waiting messages on topic [robot_description]` forever.

**Cause.** `~/.bashrc` (lines 125–127) puts every ROS 2 node in Fast DDS discovery-server mode:

```bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISCOVERY_SERVER="192.168.123.1:11811"
export FASTRTPS_DEFAULT_PROFILES_FILE=~/demo_com/super_client.xml   # SUPER_CLIENT
```

In this mode nodes only find each other through the server. 192.168.123.1 is this laptop's own
`bat0` address, but nothing listens on UDP 11811. So even nodes on the same machine never
discover each other, and `robot_state_publisher` → `create` never connects.

**Fix (pick one).**
- Start the server first, in its own terminal:
  `fastdds discovery -i 0 -l 192.168.123.1 -p 11811`
- Or run without it, in the launch terminal:
  `unset ROS_DISCOVERY_SERVER FASTRTPS_DEFAULT_PROFILES_FILE`

The relay, Gazebo and RViz terminals must all use the same choice, as well as the same
`ROS_DOMAIN_ID` (34).

**Verified 2026-09-26.** A `ros2 topic pub` / `echo` pair on the same machine got no messages with
the `.bashrc` settings, and did get messages with the two variables unset.
