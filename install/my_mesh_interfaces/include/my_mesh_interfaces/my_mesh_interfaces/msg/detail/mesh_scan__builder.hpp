// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from my_mesh_interfaces:msg/MeshScan.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/mesh_scan.hpp"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__BUILDER_HPP_
#define MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "my_mesh_interfaces/msg/detail/mesh_scan__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace my_mesh_interfaces
{

namespace msg
{

namespace builder
{

class Init_MeshScan_transmission_stamp
{
public:
  explicit Init_MeshScan_transmission_stamp(::my_mesh_interfaces::msg::MeshScan & msg)
  : msg_(msg)
  {}
  ::my_mesh_interfaces::msg::MeshScan transmission_stamp(::my_mesh_interfaces::msg::MeshScan::_transmission_stamp_type arg)
  {
    msg_.transmission_stamp = std::move(arg);
    return std::move(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshScan msg_;
};

class Init_MeshScan_map_data
{
public:
  explicit Init_MeshScan_map_data(::my_mesh_interfaces::msg::MeshScan & msg)
  : msg_(msg)
  {}
  Init_MeshScan_transmission_stamp map_data(::my_mesh_interfaces::msg::MeshScan::_map_data_type arg)
  {
    msg_.map_data = std::move(arg);
    return Init_MeshScan_transmission_stamp(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshScan msg_;
};

class Init_MeshScan_sequence_id
{
public:
  explicit Init_MeshScan_sequence_id(::my_mesh_interfaces::msg::MeshScan & msg)
  : msg_(msg)
  {}
  Init_MeshScan_map_data sequence_id(::my_mesh_interfaces::msg::MeshScan::_sequence_id_type arg)
  {
    msg_.sequence_id = std::move(arg);
    return Init_MeshScan_map_data(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshScan msg_;
};

class Init_MeshScan_session_id
{
public:
  Init_MeshScan_session_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_MeshScan_sequence_id session_id(::my_mesh_interfaces::msg::MeshScan::_session_id_type arg)
  {
    msg_.session_id = std::move(arg);
    return Init_MeshScan_sequence_id(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshScan msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::my_mesh_interfaces::msg::MeshScan>()
{
  return my_mesh_interfaces::msg::builder::Init_MeshScan_session_id();
}

}  // namespace my_mesh_interfaces

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__BUILDER_HPP_
