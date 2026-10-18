---
tags: [issue]
---
# Relay field tests 2026-10-17

Three walk tests of the Pi Zero 2 W repeater (node1, 192.168.123.3, [[Mesh network setup]]). The
laptop (192.168.123.1, running the relay) was carried, and the Pi 4 receiver (192.168.123.2, running
`tf_rolling_metrics`, [[Receiver (external)]]) stayed in place. In each test the laptop first walked
away on the direct link until the Pi stopped getting heartbeats (`/mesh/*_status`,
[[PDR measurement]]) and its metrics showed NaN. Then node1 was placed and the walk went on.
Reported by the user. Distances, TQ values and the receiver CSVs were not written down.

NaN on the Pi means a complete outage, not a missing reading ([[Known limitations]] #24).

## Results

| # | Route | node1 placed | Result |
|---|---|---|---|
| 1 | Straight line, line of sight | a few steps before the drop point | Packets went direct or not at all. Metrics stayed NaN past the drop point, even with node1 up |
| 2 | L-shaped: Pi 1.5 m from a room entrance, laptop walks into the room | at the room entrance | **Worked.** Direct link was good at the entrance and lost inside the room. With node1, the metrics were normal and `hop_count` was 2 |
| 3 | L-shaped, open, few obstacles | a few steps before the drop point | The laptop's originator table (`batctl o`) showed TQ via node1. Further on, the route went via node1 but kept flipping between direct and node1 ([[Known limitations]] #25). Pi metrics were not checked |

## Interpretation (not yet verified)

- **Why 2 worked:** the wall cuts the direct link completely. Its TQ drops to 0, so BATMAN IV has only
  one route, through node1, which can see both ends.
- **Why 1 failed:** node1 was almost as far from the Pi as the drop point was, so its own link to the
  Pi was near the range limit. The Zero's small PCB antenna probably has less range than the laptop
  too. Placing it a few steps back adds only a few steps of range. A second possible cause is the
  "grey zone": OGMs are small broadcasts at the lowest rate, so they can still arrive where data
  frames fail. The direct link then keeps a TQ that looks usable while data is lost.
- **Why 3 flips:** BATMAN IV sends each packet to the neighbour with the best TQ. A two-hop route
  multiplies both links' quality and pays the hop penalty (batman-adv default 30/255, about 12 %;
  `start-mesh.sh` does not change it). In open ground the weak direct link therefore stays close to
  the relay route. TQ is built from one OGM per second (`orig_interval` default 1000 ms), so each
  lost OGM can push the two routes past each other. Whether the flips lose packets is unknown,
  because the Pi's metrics weren't checked.

## Next tests

The test method that fixes these problems: [[Relay placement protocol]].
