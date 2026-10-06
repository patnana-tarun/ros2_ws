---
tags: [concept]
---
# Map-in-flight throttle

> **Removed on [[2026-10-05]]**, replaced by [[Relay rates]]. SLAM had started publishing
> `/map` every 2 s, the same as the 2 s hold, so each map re-armed the hold before it ran out.
> The flag never cleared and TF was throttled the whole time (2302 of 2303 TF messages flagged
> in one test). This note describes the design as it was.

While a map is crossing the mesh, [[mesh_nodes]] reduces how much TF it sends, so TF does not
compete with the map for airtime.

```
/map ─► publish MeshMap ─► map_in_flight = True ─► (re)start one-shot timer(hold_sec) ─► False

/tf ─► map_in_flight?
        no  ─► forward, reset counter
        yes ─► counter++; slot = (counter−1) mod total
                 slot < send ─► forward with map_in_flight=True
                 else        ─► drop on purpose (uses no sequence_id)
```

Defaults: 2 of every 5 messages forwarded, 2 s hold ([[mesh_nodes]] parameters). The hold and
the status heartbeats run on the wall clock, not sim time: mesh airtime is real time, and with
sim time a stalled `/clock` would leave the throttle on forever. A hold of 0 turns the throttle off.

## Design choices
- **One process for map and TF.** The flag is an in-process bool. As a separate topic it could
  itself be lost on the mesh, and then throttling would fail exactly when it is needed.
- **Fixed hold time.** This layer has no delivery ACK. Tune the hold to roughly 2× the
  observed map latency (receive time − `transmission_stamp`).
- **A new map restarts the timer**, so the hold always runs from the latest map.
- **The flag is sent in every `MeshTf`.** This lets the receiver tell a deliberate rate drop
  apart from real loss ([[PDR measurement]]).
