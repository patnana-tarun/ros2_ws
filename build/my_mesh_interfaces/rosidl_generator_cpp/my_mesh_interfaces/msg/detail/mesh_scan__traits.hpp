// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from my_mesh_interfaces:msg/MeshScan.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/mesh_scan.hpp"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__TRAITS_HPP_
#define MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "my_mesh_interfaces/msg/detail/mesh_scan__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'map_data'
#include "nav_msgs/msg/detail/occupancy_grid__traits.hpp"
// Member 'transmission_stamp'
#include "builtin_interfaces/msg/detail/time__traits.hpp"

namespace my_mesh_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const MeshScan & msg,
  std::ostream & out)
{
  out << "{";
  // member: session_id
  {
    out << "session_id: ";
    rosidl_generator_traits::value_to_yaml(msg.session_id, out);
    out << ", ";
  }

  // member: sequence_id
  {
    out << "sequence_id: ";
    rosidl_generator_traits::value_to_yaml(msg.sequence_id, out);
    out << ", ";
  }

  // member: map_data
  {
    out << "map_data: ";
    to_flow_style_yaml(msg.map_data, out);
    out << ", ";
  }

  // member: transmission_stamp
  {
    out << "transmission_stamp: ";
    to_flow_style_yaml(msg.transmission_stamp, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const MeshScan & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: session_id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "session_id: ";
    rosidl_generator_traits::value_to_yaml(msg.session_id, out);
    out << "\n";
  }

  // member: sequence_id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "sequence_id: ";
    rosidl_generator_traits::value_to_yaml(msg.sequence_id, out);
    out << "\n";
  }

  // member: map_data
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "map_data:\n";
    to_block_style_yaml(msg.map_data, out, indentation + 2);
  }

  // member: transmission_stamp
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "transmission_stamp:\n";
    to_block_style_yaml(msg.transmission_stamp, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const MeshScan & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace my_mesh_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use my_mesh_interfaces::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const my_mesh_interfaces::msg::MeshScan & msg,
  std::ostream & out, size_t indentation = 0)
{
  my_mesh_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use my_mesh_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const my_mesh_interfaces::msg::MeshScan & msg)
{
  return my_mesh_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<my_mesh_interfaces::msg::MeshScan>()
{
  return "my_mesh_interfaces::msg::MeshScan";
}

template<>
inline const char * name<my_mesh_interfaces::msg::MeshScan>()
{
  return "my_mesh_interfaces/msg/MeshScan";
}

template<>
struct has_fixed_size<my_mesh_interfaces::msg::MeshScan>
  : std::integral_constant<bool, has_fixed_size<builtin_interfaces::msg::Time>::value && has_fixed_size<nav_msgs::msg::OccupancyGrid>::value> {};

template<>
struct has_bounded_size<my_mesh_interfaces::msg::MeshScan>
  : std::integral_constant<bool, has_bounded_size<builtin_interfaces::msg::Time>::value && has_bounded_size<nav_msgs::msg::OccupancyGrid>::value> {};

template<>
struct is_message<my_mesh_interfaces::msg::MeshScan>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__TRAITS_HPP_
