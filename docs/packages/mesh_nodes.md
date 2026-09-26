---
tags: [package]
path: src/mesh_nodes
build_type: ament_python
---
# mesh_nodes

Holds `explorer_relay_node` (executable `explorer_relay`). The node forwards `/map` and `/tf` to
`/mesh/*` (see [[Topics]]) using the [[Message envelope]], [[QoS design]] and
[[Map-in-flight throttle]].

## Files
| File                               | Role                                   |
|------------------------------------|----------------------------------------|
| `mesh_nodes/explorer_relay_node.py`| the node                               |
| `launch/explorer_relay.launch.py`  | launch arguments `params_file`, `use_sim_time` |
| `config/explorer_relay.yaml`       | default parameters                     |

## Run
```bash
ros2 launch mesh_nodes explorer_relay.launch.py                   # add use_sim_time:=true with Gazebo
ros2 run mesh_nodes explorer_relay --ros-args -p map_in_flight_hold_sec:=3.0
```

## Parameters
Parameters are read once at startup. `ros2 param set` has no effect while the node is running.

| Name                     | Default | Clamp                | Meaning                                  |
|--------------------------|---------|----------------------|------------------------------------------|
| `tf_throttle_send`       | 2       | ≥ 1                  | TF messages forwarded per window during a map transfer |
| `tf_throttle_total`      | 5       | ≥ `tf_throttle_send` | Size of that window                      |
| `map_in_flight_hold_sec` | 2.0     | ≥ 0                  | How long the mesh counts as busy after each `/map` |

Depends on [[my_mesh_interfaces]].
