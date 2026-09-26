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

## Heartbeat rates
| Topic              | Rate | Why                                                    |
|--------------------|------|--------------------------------------------------------|
| `/mesh/map_status` | 1 Hz | maps are infrequent                                    |
| `/mesh/tf_status`  | 5 Hz | the [[Map-in-flight throttle]] can switch on and off within 1 s |

**Why 5 Hz for TF:** with a 1 Hz heartbeat, a rolling window crossing a throttle switch used a
heartbeat up to ~1 s old, so `expected` was wrong at the window edges. In practice PDR swung
with `throttle_active_fraction` while TQ (which does not depend on the heartbeat) stayed flat,
so the dips came from measurement quantisation and not from the link. `SenderStatus` is two
uint64 values, so 5 Hz costs almost no airtime.

TF messages that the throttle drops on purpose do not use up a `sequence_id`, so they never
count as loss.
