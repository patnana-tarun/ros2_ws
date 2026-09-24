cmake_minimum_required(VERSION 3.8)
project(my_mesh_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(tf2_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/MeshScan.msg"
  "msg/MeshMap.msg"
  "msg/MeshTf.msg"
  "msg/SenderStatus.msg"
  DEPENDENCIES
  sensor_msgs
  builtin_interfaces
  nav_msgs
  tf2_msgs
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
