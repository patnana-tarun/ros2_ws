---
tags: [package]
path: src/mesh_nodes
build_type: ament_python
---
# mesh_nodes

Holds `explorer_relay_node` (executable `explorer_relay`). The node forwards `/map` and `/tf` to
`/mesh/*` (see [[Topics]]) using the [[Message envelope]], [[QoS design]] and
[[Relay rates]] (before 2026-10-05: [[Map-in-flight throttle]]).

## Files
| File                               | Role                                   |
|------------------------------------|----------------------------------------|
| `mesh_nodes/explorer_relay_node.py`| the node                               |
| `launch/explorer_relay.launch.py`  | launch arguments `params_file`, `use_sim_time` |
| `config/explorer_relay.yaml`       | default parameters                     |

## Run
```bash
ros2 launch mesh_nodes explorer_relay.launch.py                   # add use_sim_time:=true with Gazebo
ros2 run mesh_nodes explorer_relay --ros-args -p map_publish_period_sec:=3.0 -p tf_decimation:=3
```

## Parameters
Parameters are read once at startup. `ros2 param set` has no effect while the node is running.

| Name                     | Default | Clamp  | Meaning                                       |
|--------------------------|---------|--------|-----------------------------------------------|
| `map_publish_period_sec` | 3.0     | ≥ 0.1  | The latest `/map` is sent every this many seconds |
| `tf_decimation`          | 3       | ≥ 1    | 1 of every N `/tf` messages is forwarded, per TF source |

Depends on [[my_mesh_interfaces]].
