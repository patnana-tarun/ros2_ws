---
tags: [external]
---
# Receiver (external)

The receiver's code is **not in this repo**. It runs on the receiver Pi (`fyp@192.168.123.2`,
hostname `fyp-desktop`, reached over `bat0`), in the package `~/ros2_ws/src/mesh_nodes`. The
package has the same name as this repo's sender [[mesh_nodes]], so the two can't share a workspace.

| Executable              | What it does |
|-------------------------|--------------|
| `tf_rolling_metrics`    | Rolling-window PDR, latency, jitter and throughput for `/mesh/tf` ([[PDR measurement]]); `hop_count`/`tq` from `batctl`. Starts idle and logs 60 s runs on `start` ([[Run logging]]). Writes two CSVs and a black-box log, republishes TF on `/tf_recovered` |
| `raw_mesh_event_logger` | Passive control: one CSV row per `/mesh/*` message, with no windowing or maths |

```bash
ros2 launch mesh_nodes receiver.launch.py explorer_mac:=28:a4:4a:ac:3c:1c   # the laptop's wlan MAC
```

Deployed and tested over the mesh on [[2026-09-29]]. The old loose scripts and their `.pre_*` backups are kept in
`~/ros2_ws/backup/mesh_nodes_loose_2026-09-29/`. The version before [[Run logging]] (node + `receiver.yaml`) is in
`~/ros2_ws/backup/mesh_nodes_2026-10-05/`.

Related files on the laptop, in `~/Downloads`:

| File                                   | What it is                                          |
|----------------------------------------|-----------------------------------------------------|
| `tf_rollling_mectrics_node.py`         | an older copy of the receiver node                  |
| `tf_rolling_test_01.csv`, `tf_rolling_text_05.csv` | recorded test runs                       |
| `tf_blackbox.log`                      | raw log                                             |
| `mesh_telemetry_dashboard*.html`, `telemetry_explorer.html` | result dashboards                |
| `explorer_robot_technical_blueprint.md`| earlier design notes                                |
| `07-brcmfmac-ibss-rssi-research.md`    | Wi-Fi driver (IBSS/RSSI) research                   |

The receiver must use QoS compatible with [[QoS design]] and consume the topics in [[Topics]].
Both machines use Fast DDS discovery-server mode, so the server on the laptop must be running
([[Discovery server not running]]). Its open issues are in [[Known limitations]].
