---
tags: [concept]
---
# Map freshness requirement

The project's requirement for the map at the base station, set by the user on [[2026-10-22]].
The map matters more than TF ([[QoS design]]). As range grows, the base station need not get
every map, but:

| Level | Maps missed in a row | Gap between map arrivals ([[Relay rates]]: one map every 3 s) |
|---|---|---|
| Ideal | 0 | about 3 s |
| Target | **at most 1** | about 6 s |
| Hard limit | **at most 2**, never more | about 9 s |

A gap counts as `k = round(gap / 3 s) − 1` missed maps. The user first set 5 s / 9 s, then
changed the target to one missed map the same day.

**How to measure:** the gap between consecutive map arrivals at the receiver. In the
[[Run logging]] CSVs, it is the time between consecutive rows with `map_active` = 1 within a run,
to 1 s resolution. A related measure is map age: now minus the `transmission_stamp`
([[Message envelope]]) of the newest map received. The combined PDR ([[PDR measurement]]) is no use here. TF dominates the packet count,
and because the map is RELIABLE, a weak link shows up as delay before maps are lost.

**Where it applies:** the link-quality score and the relay-deployment rule
([[Relay placement protocol]]). A relay must be in place before two maps in a row are missed,
and preferably while at most one is.
