// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from my_mesh_interfaces:msg/MeshTf.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/mesh_tf.h"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__MESH_TF__STRUCT_H_
#define MY_MESH_INTERFACES__MSG__DETAIL__MESH_TF__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// Constants defined in the message

// Include directives for member types
// Member 'transmission_stamp'
#include "builtin_interfaces/msg/detail/time__struct.h"
// Member 'tf_data'
#include "tf2_msgs/msg/detail/tf_message__struct.h"

/// Struct defined in msg/MeshTf in the package my_mesh_interfaces.
typedef struct my_mesh_interfaces__msg__MeshTf
{
  uint64_t session_id;
  uint64_t sequence_id;
  builtin_interfaces__msg__Time transmission_stamp;
  tf2_msgs__msg__TFMessage tf_data;
  bool map_in_flight;
} my_mesh_interfaces__msg__MeshTf;

// Struct for a sequence of my_mesh_interfaces__msg__MeshTf.
typedef struct my_mesh_interfaces__msg__MeshTf__Sequence
{
  my_mesh_interfaces__msg__MeshTf * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} my_mesh_interfaces__msg__MeshTf__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__MESH_TF__STRUCT_H_
