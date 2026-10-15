---
tags: [concept]
---
# Relay rates

How often `/tf` and `/map` reach the mesh. This replaced the [[Map-in-flight throttle]] on
[[2026-10-05]].

## Since 2026-10-15: the robot uses full-rate TF, the relay sends a third
The TF sources run at full rate again, so EKF, SLAM and Nav2 on the robot get all of it. The
relay forwards 1 of every 3 `/tf` messages per source (`tf_decimation: 3`). Each `/map` is still
forwarded as it arrives, every 3 s.

| Source | Rate on the robot (`/tf`) | Rate on the mesh (`/mesh/tf`) |
|---|---|---|
| SLAM `map → odom` (`transform_publish_period` 0.02 s) | 50.0–53.3 /s | 16.7 /s |
| EKF `odom → base_footprint` (`frequency` 30 Hz) | 30.0 /s | 10.0 /s |
| robot_state_publisher, wheel and bogie joints (20 Hz default) | 20.0 /s | 6.7 /s |
| **Total** | 100–103 /s | 33.3 /s |

Measured on 2026-10-15 in 3 GUI cave runs (relay with `use_sim_time:=true`, 30 s count, local
discovery). The mesh load is the same as with the 2026-10-06 setup below. The `/map` rate and
size don't change.

**Why raw `/tf` stays off the mesh.** DDS sends a topic's data only to matched subscribers. The
receiver subscribes to `/mesh/*`, not `/tf`, so the full-rate `/tf` never leaves the laptop. That
stops being true if a node on the receiver subscribes to `/tf` (RViz, `ros2 topic echo /tf`).
A separate ROS domain for the robot stack would rule that out, at the cost of a two-domain relay.
Not yet checked with the receiver connected.

**Why the change.** At 10 Hz the EKF made the startup turn overshoot by 140° on average and spin
up to 4 full turns ([[Baseline runs 2026-10-08]]).

## 2026-10-06 to 2026-10-15: the sources published less, and the relay forwarded everything
The publishers themselves ran at a third of their earlier rates, and [[mesh_nodes]] forwarded
every message as it arrived.

| Source | Setting | Before | 2026-10-06 | Measured |
|---|---|---|---|---|
| SLAM `map → odom` | `transform_publish_period` ([[Navigation stack]]) | 0.02 s (50 Hz) | 0.06 s (16.7 Hz) | 16.2 /s |
| EKF `odom → base_footprint` | `frequency` ([[Odometry fusion]]) | 30 Hz | 10 Hz | 9.4 /s |
| robot_state_publisher, wheel and bogie joints | `publish_frequency` (sim and real launch files) | 20 Hz (default) | 6.67 Hz | 6.1 /s |
| **`/tf` total** | | ~95–100 /s | ~33 /s | 31.7 /s |
| SLAM `/map` | `map_update_interval` | 2 s | 3 s | every 3.0 s |

Measured in a headless cave simulation on the laptop (60 s warm-up, 30 s count, real-time
factor 0.97). The relay forwarded 32.3 `/mesh/tf` per second and one `/mesh/map` every
3.0 s. In the same run, Nav2 reached 2 exploration goals, and no TF timeouts appeared apart
from the usual wait at startup before the EKF is up. The Pi receives what the relay sends, so
its metrics count a third of the old TF rate and one map every 3 s
([[PDR measurement]], [[Run logging]]).

## 2026-10-05: the relay reduced the rates itself
For one day the sources ran at full rate and the relay thinned them out (the same TF setup as
since 2026-10-15): 1 of every 3 TF
messages (counted per source, i.e. per set of child frames, so one source couldn't be
starved), and the latest map on a fixed 3 s timer. The mesh load was the same, but every
node on the robot still ran at full rate. Laptop test with fake sources: 267 TF forwarded
per 10 s out of 80 msg/s, 3 maps per 10 s.

## Common to all
- **Relay parameters:** with `map_publish_period_sec` at 0 (default), each `/map` is forwarded as
  it arrives; a value above 0 publishes the latest `/map` on that timer instead.
  `tf_decimation` (default 3) forwards 1 of every N `/tf` messages, counted per TF source.
- **Skipped TF uses no `sequence_id`**, so it never counts as loss.
- **Map heartbeat right after each map.** `/mesh/map_status` runs at 1 Hz and is also sent
  straight after every map, so the receiver's expected map count is exact.
- Maps grow as the cave is explored: about 11 KB at the start, ~109 KB measured on
  2026-10-05, up to about 150 KB for the whole 23 × 16.5 m cave at 0.05 m.
- `MeshTf.map_in_flight` is still in the message, so the receiver's interface doesn't
  change, but it is always `false`.
