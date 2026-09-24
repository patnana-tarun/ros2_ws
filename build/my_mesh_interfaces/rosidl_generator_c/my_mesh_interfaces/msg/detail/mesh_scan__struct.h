// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from my_mesh_interfaces:msg/MeshScan.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/mesh_scan.h"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__STRUCT_H_
#define MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// Constants defined in the message

// Include directives for member types
// Member 'map_data'
#include "nav_msgs/msg/detail/occupancy_grid__struct.h"
// Member 'transmission_stamp'
#include "builtin_interfaces/msg/detail/time__struct.h"

/// Struct defined in msg/MeshScan in the package my_mesh_interfaces.
typedef struct my_mesh_interfaces__msg__MeshScan
{
  uint64_t session_id;
  uint64_t sequence_id;
  nav_msgs__msg__OccupancyGrid map_data;
  builtin_interfaces__msg__Time transmission_stamp;
} my_mesh_interfaces__msg__MeshScan;

// Struct for a sequence of my_mesh_interfaces__msg__MeshScan.
typedef struct my_mesh_interfaces__msg__MeshScan__Sequence
{
  my_mesh_interfaces__msg__MeshScan * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} my_mesh_interfaces__msg__MeshScan__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__STRUCT_H_
