// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__rosidl_typesupport_fastrtps_cpp.hpp.em
// with input from my_mesh_interfaces:msg/MeshScan.idl
// generated code does not contain a copyright notice

#ifndef MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_
#define MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_

#include <cstddef>
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_interface/macros.h"
#include "my_mesh_interfaces/msg/rosidl_typesupport_fastrtps_cpp__visibility_control.h"
#include "my_mesh_interfaces/msg/detail/mesh_scan__struct.hpp"

#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-parameter"
# ifdef __clang__
#  pragma clang diagnostic ignored "-Wdeprecated-register"
#  pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
# endif
#endif
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif

#include "fastcdr/Cdr.h"

namespace my_mesh_interfaces
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
cdr_serialize(
  const my_mesh_interfaces::msg::MeshScan & ros_message,
  eprosima::fastcdr::Cdr & cdr);

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  my_mesh_interfaces::msg::MeshScan & ros_message);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
get_serialized_size(
  const my_mesh_interfaces::msg::MeshScan & ros_message,
  size_t current_alignment);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
max_serialized_size_MeshScan(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
cdr_serialize_key(
  const my_mesh_interfaces::msg::MeshScan & ros_message,
  eprosima::fastcdr::Cdr &);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
get_serialized_size_key(
  const my_mesh_interfaces::msg::MeshScan & ros_message,
  size_t current_alignment);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
max_serialized_size_key_MeshScan(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace my_mesh_interfaces

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
const rosidl_message_type_support_t *
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, my_mesh_interfaces, msg, MeshScan)();

#ifdef __cplusplus
}
#endif

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_
