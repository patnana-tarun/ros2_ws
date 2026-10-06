---
tags: [concept]
---
# Message envelope

Every relayed message ([[my_mesh_interfaces]]) carries these fields:

| Field                | Meaning                                                                  |
|----------------------|--------------------------------------------------------------------------|
| `session_id`         | Random 63-bit value, fixed for the node's lifetime. A new value means the sender restarted. |
| `sequence_id`        | Monotonic counter, one for map and one for TF. A gap means a lost message. |
| `transmission_stamp` | Sender **wall clock** (system time) at publish time, used to measure latency. Wall time even with `use_sim_time:=true`, because the receiver compares it with its own clock. Latency is only valid when both machines' clocks are synced (e.g. chrony). |

This layer has no acks and no retries. The receiver detects loss from `sequence_id` gaps
([[PDR measurement]]). DDS retransmits only the map stream ([[QoS design]]).
