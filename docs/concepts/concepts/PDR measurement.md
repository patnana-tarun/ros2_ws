---
tags: [concept]
---
# PDR measurement

The receiver ([[Receiver (external)]]) computes packet delivery ratio from the
[[Message envelope]] and the `SenderStatus` heartbeats.

```
expected = last_sequence_sent (heartbeat) − first sequence_id in window
received = distinct sequence_ids received in window
PDR      = received / expected
```

Since [[2026-10-05]], one PDR covers both streams ([[Run logging]]):

```
PDR = (TF received + maps received) / (TF expected + maps expected)
```

Each expected count comes from its own heartbeat.

**Received is counted by sequence range, not by time** (since 2026-10-05). The heartbeats
give a range of sequence ids (start, end] sent in the window; received = distinct ids inside
that same range. Before, received was every packet that arrived in the last span. Packets newer
than the latest heartbeat (up to 0.2 s of TF) then counted as received but not expected.
TF received exceeded expected in 100 of 240 rows, by up to 17, and the 100 % cap hid it, so
real loss of a few packets disappeared. The TF counter only counts the forwarded
third ([[Relay rates]]), so the expected TF count is already 1/3 of the real TF rate. TF and
map PDR are also written separately.

## Heartbeat rates
| Topic              | Rate | Why                                                    |
|--------------------|------|--------------------------------------------------------|
| `/mesh/map_status` | 1 Hz, plus one right after each map | maps are infrequent; the extra one makes the map count exact |
| `/mesh/tf_status`  | 5 Hz | the old [[Map-in-flight throttle]] could switch on and off within 1 s |

**Why 5 Hz for TF:** with a 1 Hz heartbeat, a rolling window crossing a throttle switch used a
heartbeat up to ~1 s old, so `expected` was wrong at the window edges. In practice PDR swung
with `throttle_active_fraction` while TQ (which does not depend on the heartbeat) stayed flat,
so the dips came from measurement quantisation and not from the link. `SenderStatus` is two
uint64 values, so 5 Hz costs almost no airtime.

TF messages skipped on purpose (by [[Relay rates]], earlier by the throttle) do not use up a
`sequence_id`, so they never count as loss.
