// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from my_mesh_interfaces:msg/SenderStatus.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/sender_status.h"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__STRUCT_H_
#define MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// Constants defined in the message

/// Struct defined in msg/SenderStatus in the package my_mesh_interfaces.
typedef struct my_mesh_interfaces__msg__SenderStatus
{
  uint64_t session_id;
  uint64_t last_sequence_sent;
} my_mesh_interfaces__msg__SenderStatus;

// Struct for a sequence of my_mesh_interfaces__msg__SenderStatus.
typedef struct my_mesh_interfaces__msg__SenderStatus__Sequence
{
  my_mesh_interfaces__msg__SenderStatus * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} my_mesh_interfaces__msg__SenderStatus__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__STRUCT_H_
