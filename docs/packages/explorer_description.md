---
tags: [package]
path: src/explorer_description
build_type: ament_cmake (install + cave generation)
---
# explorer_description

The explorer's URDF and its Gazebo Harmonic simulation. Contents are covered in
[[Robot model]], [[Gazebo simulation]] and [[Cave world]].

| File                               | Role                                             |
|------------------------------------|--------------------------------------------------|
| `urdf/explorer.urdf.xacro`         | links, joints, inertias ([[Robot model]])         |
| `urdf/explorer_gazebo.xacro`       | friction, drive, joint states, LiDAR ([[Gazebo simulation]]) |
| `launch/explorer_gazebo.launch.py` | Gazebo + robot_state_publisher + spawn + bridge + optional RViz |
| `rviz/explorer.rviz`               | RobotModel, TF, `/scan`, `/map`; fixed frame `odom` |
| `scripts/generate_cave.py`         | generates the cave meshes, textures and worlds at build time ([[Cave world]]) |

## Run
```bash
ros2 launch explorer_description explorer_gazebo.launch.py rviz:=true   # world:=cave.sdf
ros2 run turtlebot3_teleop teleop_keyboard                              # drive it (TwistStamped)
```

## Check the model
```bash
xacro src/explorer_description/urdf/explorer.urdf.xacro > /tmp/e.urdf && check_urdf /tmp/e.urdf
```
The include uses `$(find explorer_description)`, so the workspace has to be built and sourced
first.
