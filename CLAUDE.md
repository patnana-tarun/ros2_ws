# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A ROS 2 (Jazzy) colcon workspace for relaying a robot's SLAM output (`/map`, `/tf`) across a
lossy BATMAN-adv mesh network to a receiver. It has two parts on very different footing:

- `src/my_mesh_interfaces/` — a real ament_cmake interface package (the only package `colcon`
  knows about) defining the custom mesh messages.
- `mesh_nodes/` — plain Python scripts, *not* an ament/ROS package (no `package.xml`, no
  `setup.py`). They are run directly with `python3`, not via `ros2 run`/`ros2 launch`.

This is the sender/explorer side only. Comments in `explorer_relay_node.py` reference a
receiver-side counterpart (`tf_rolling_metrics_node.py`, computing a rolling-window PDR from
`SenderStatus` heartbeats) that does not exist anywhere in this workspace — it lives on/for the
receiving robot, outside this repo.

## Commands

Build the interfaces package (must be done before running any node, since the mesh nodes import
`my_mesh_interfaces.msg`):

```bash
colcon build --packages-select my_mesh_interfaces
source install/setup.bash
```

Run the explorer relay node directly (requires the workspace to be sourced as above, plus a
normal ROS 2 environment with `rclpy`, `nav_msgs`, `tf2_msgs` available):

```bash
python3 mesh_nodes/explorer_relay_node.py
```

There is no test suite and no linter configured in this workspace.

## Architecture: explorer_relay_node.py

Single node that forwards both `/map` and `/tf` onto the mesh, deliberately combined into one
process so the "map is mid-transmission" signal can be a plain in-process bool instead of another
topic that could itself be lost on the lossy link.

**Message envelope**: every relayed message (`MeshMap`, `MeshTf`) carries `session_id` (random
per node-lifetime, `MeshScan`/`SenderStatus` share the same pattern), a monotonic
`sequence_id`, and a `transmission_stamp`. The receiver uses gaps in `sequence_id` (compared
against `SenderStatus.last_sequence_sent` heartbeats) to compute packet delivery ratio — there is
no ack/retry at this layer.

**QoS is asymmetric by design and must match the receiver exactly** (DDS won't connect a
RELIABLE subscriber to a BEST_EFFORT publisher or vice versa):
- Map: `RELIABLE` + `TRANSIENT_LOCAL` — a lost map packet has no "next sample" to correct it.
- TF: `BEST_EFFORT` + `VOLATILE` — tf is high-rate and self-healing (a dropped sample is
  superseded by the next one), so paying DDS retransmission cost for it just burns mesh airtime.

**Map-in-flight / TF throttling**: on every `/map` publish, `map_in_flight` is set `True` and a
one-shot timer clears it after `map_in_flight_hold_sec` (default 2s) — a fixed approximation of
mesh clear time, since there's no delivery ACK at this layer to wait on instead. While
`map_in_flight` is `True`, `/tf` is throttled to `tf_throttle_send`-out-of-`tf_throttle_total`
consecutive messages (default 2-of-5), trading tf freshness for map airtime during exactly the
window they'd compete for the channel. Each forwarded `MeshTf` carries `map_in_flight` explicitly
(not left for the receiver to infer from rate) so a rate drop is legible as "throttled for a map
transfer," not packet loss.

**Status heartbeats**: `SenderStatus` (session_id + last_sequence_sent) is published separately
per stream — 1Hz for map, 5Hz for tf. The tf rate is intentionally higher than a "just a
heartbeat" cadence would need: the receiver's rolling-window PDR calculation derives its expected
message count from these heartbeats, and a coarser heartbeat produces PDR that oscillates with
the throttle state at window edges rather than degrading smoothly with actual link quality.

## Interfaces package (`src/my_mesh_interfaces`)

Defines `MeshMap`, `MeshTf`, `MeshScan`, `SenderStatus`. `MeshScan` (wraps `OccupancyGrid`,
despite the name) is defined but currently has no corresponding relay node in this workspace.
