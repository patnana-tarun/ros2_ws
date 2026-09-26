---
tags: [external]
---
# Receiver (external)

The receiving robot's code is **not in this repo**. Related files are in `~/Downloads`:

| File                                   | What it is                                          |
|----------------------------------------|-----------------------------------------------------|
| `tf_rollling_mectrics_node.py`         | receiver node: rolling PDR and latency ([[PDR measurement]]) |
| `tf_rolling_test_01.csv`, `tf_rolling_text_05.csv` | recorded test runs                       |
| `tf_blackbox.log`                      | raw log                                             |
| `mesh_telemetry_dashboard*.html`, `telemetry_explorer.html` | result dashboards                |
| `explorer_robot_technical_blueprint.md`| earlier design notes                                |
| `07-brcmfmac-ibss-rssi-research.md`    | Wi-Fi driver (IBSS/RSSI) research                   |

The receiver must use QoS compatible with [[QoS design]] and consume the topics in [[Topics]].
