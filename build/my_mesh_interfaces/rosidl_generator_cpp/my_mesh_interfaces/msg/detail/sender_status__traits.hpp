// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from my_mesh_interfaces:msg/SenderStatus.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/sender_status.hpp"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__TRAITS_HPP_
#define MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "my_mesh_interfaces/msg/detail/sender_status__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace my_mesh_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const SenderStatus & msg,
  std::ostream & out)
{
  out << "{";
  // member: session_id
  {
    out << "session_id: ";
    rosidl_generator_traits::value_to_yaml(msg.session_id, out);
    out << ", ";
  }

  // member: last_sequence_sent
  {
    out << "last_sequence_sent: ";
    rosidl_generator_traits::value_to_yaml(msg.last_sequence_sent, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const SenderStatus & msg,
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

  // member: last_sequence_sent
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "last_sequence_sent: ";
    rosidl_generator_traits::value_to_yaml(msg.last_sequence_sent, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const SenderStatus & msg, bool use_flow_style = false)
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
  const my_mesh_interfaces::msg::SenderStatus & msg,
  std::ostream & out, size_t indentation = 0)
{
  my_mesh_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use my_mesh_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const my_mesh_interfaces::msg::SenderStatus & msg)
{
  return my_mesh_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<my_mesh_interfaces::msg::SenderStatus>()
{
  return "my_mesh_interfaces::msg::SenderStatus";
}

template<>
inline const char * name<my_mesh_interfaces::msg::SenderStatus>()
{
  return "my_mesh_interfaces/msg/SenderStatus";
}

template<>
struct has_fixed_size<my_mesh_interfaces::msg::SenderStatus>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<my_mesh_interfaces::msg::SenderStatus>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<my_mesh_interfaces::msg::SenderStatus>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__TRAITS_HPP_
