---
tags: [concept]
---
# Relay rates

Since [[2026-10-05]], [[mesh_nodes]] sends both streams at fixed, reduced rates. This replaced
the [[Map-in-flight throttle]].

| Stream | Rule | Parameter (default) |
|---|---|---|
| Map | The latest `/map` is published every 3 s, whether or not it changed. SLAM itself publishes every 2 s ([[Navigation stack]]); the relay just keeps the newest one | `map_publish_period_sec` (3.0) |
| TF | 1 of every 3 `/tf` messages is forwarded, so a third of the real rate | `tf_decimation` (3) |

- **Per-source decimation.** The 1-in-3 count is kept separately for each TF source (the set of
  child frames in the message, e.g. the EKF's `base_footprint` or the six wheel joints). One
  shared counter over the mixed stream could line up with the sources' publish pattern and
  starve one of them.
- **Skipped TF uses no `sequence_id`**, so the receiver's expected count is already the
  forwarded third ([[PDR measurement]]).
- **Map heartbeat right after each map.** `/mesh/map_status` still runs at 1 Hz, but it is also
  sent straight after every map, so the receiver's expected map count is exact and not up to
  1 s stale.
- **Fixed map period** gives a known expected map count per window. It also keeps the map
  load predictable, although each map grows as the cave is explored: about 11 KB at the
  start, up to about 150 KB for the whole 23 × 16.5 m cave at 0.05 m.
- `MeshTf.map_in_flight` is still in the message, so the receiver's interface doesn't change,
  but it is always `false`.

Measured on the laptop with fake sources (TF 80 msg/s from two sources, a 30 000-cell map)
on [[2026-10-05]]: 267 TF forwarded per 10 s (1/3), 3 maps per 10 s.
