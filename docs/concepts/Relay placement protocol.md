---
tags: [concept]
---
# Relay placement protocol

How to collect the data for the relay-drop threshold and for the two-hop behaviour. Full step-by-step
version with commands, checklists and a diagram:
[Relay placement: test protocol](https://claude.ai/code/artifact/612a504b-0e6c-46bf-90d8-05a6a19f2df6)
(Claude Doc, 2026-10-18). It answers the problems in [[Relay field tests 2026-10-17]].

## Key ideas
- **The drop point decides the relay's link to the Pi.** The relay lands where the rover stands, so
  dropped at the edge it starts on a dying link. Roughly, TQ via node1 ≈ TQ(node1→Pi) × 225/255 ×
  TQ(rover→node1)/255 (default `hop_penalty` 30). node1→Pi ~150 gives ~132 via node1; ~240 gives ~212.
- **Direct while direct is better is correct**, not a wasted relay.
- **TQ lags about a minute** (64 OGMs at 1/s). Measure standing still, 60 s wait + 60 s run per point.
- **Delivery falls off a cliff, RSSI falls smoothly.** Plot against RSSI, trigger on RSSI margin.

## Phases
| Phase | node1 | What it gives |
|---|---|---|
| A | off | curves vs RSSI, the cliff RSSI, training rows |
| B | on, direct link blocked with an nftables `netdev` ingress rule on both ends | clean two-hop cost |
| C | dropped at cliff +0/5/10/15 dB, free routing | the margin for one clean switch |

Then fit a logistic regression: rover-side inputs (RSSI median and spread, TQ, retry and failure
rate), normalised to 0–1; label = PDR < 90 % here or at the next two points. Leave-one-pass-out
cross-validation. Threshold = the score at Phase C's clean-switch margin, smoothed over 5–10 s.
Validate on a fresh run.

## Main mistakes
Dropping at the edge; reading TQ while walking; plotting against distance; carrying the laptop by
hand (body + height); NaN treated as missing ([[Known limitations]] #24); node1 left on in Phase A;
nft block left in place; PDR used as a trigger input (the rover doesn't have it in time).
