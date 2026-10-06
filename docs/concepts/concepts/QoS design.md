---
tags: [concept]
---
# QoS design

Each stream gets different QoS on purpose. The per-topic values are in [[Topics]].

| Stream | QoS                          | Why |
|--------|------------------------------|-----|
| Map    | RELIABLE + TRANSIENT_LOCAL   | A lost map has no later sample to replace it, and late joiners need the latest map. |
| TF     | BEST_EFFORT + VOLATILE       | TF is high-rate and self-correcting: the next sample replaces a dropped one. Retransmitting it wastes mesh airtime and adds latency. |

**Compatibility rule:** a RELIABLE subscriber will not connect to a BEST_EFFORT publisher. The
reverse works. The receiver has to follow this rule ([[Receiver (external)]]).
