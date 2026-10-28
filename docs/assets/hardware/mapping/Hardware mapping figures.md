---
tags: [moc]
---
# Hardware mapping figures

Figures for [[Hardware bring-up]] (step 7) and [[Hardware test tools]].

- `fake_robot_hand_map.png`: the map `mapping.launch.py` built on `fake_robot` from a
  hand-style route (2.8 m ahead, left, 1.4 m, right, 1.6 m through the doorway), saved with
  `map_saver_cli` (2026-10-28). 182 × 123 cells at 5 cm = 9.1 × 6.15 m for the 9 × 6 m world:
  both rooms, the doorway, the pillar (top left) and the box's near face (right; its far side
  stays unknown, grey). Drawn from the saved `.pgm` scaled 4× (PIL, nearest neighbour).
