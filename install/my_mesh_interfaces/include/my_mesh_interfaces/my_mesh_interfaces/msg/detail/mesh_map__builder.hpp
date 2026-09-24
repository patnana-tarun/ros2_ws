// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from my_mesh_interfaces:msg/MeshMap.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/mesh_map.hpp"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__MESH_MAP__BUILDER_HPP_
#define MY_MESH_INTERFACES__MSG__DETAIL__MESH_MAP__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "my_mesh_interfaces/msg/detail/mesh_map__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace my_mesh_interfaces
{

namespace msg
{

namespace builder
{

class Init_MeshMap_map_data
{
public:
  explicit Init_MeshMap_map_data(::my_mesh_interfaces::msg::MeshMap & msg)
  : msg_(msg)
  {}
  ::my_mesh_interfaces::msg::MeshMap map_data(::my_mesh_interfaces::msg::MeshMap::_map_data_type arg)
  {
    msg_.map_data = std::move(arg);
    return std::move(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshMap msg_;
};

class Init_MeshMap_transmission_stamp
{
public:
  explicit Init_MeshMap_transmission_stamp(::my_mesh_interfaces::msg::MeshMap & msg)
  : msg_(msg)
  {}
  Init_MeshMap_map_data transmission_stamp(::my_mesh_interfaces::msg::MeshMap::_transmission_stamp_type arg)
  {
    msg_.transmission_stamp = std::move(arg);
    return Init_MeshMap_map_data(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshMap msg_;
};

class Init_MeshMap_sequence_id
{
public:
  explicit Init_MeshMap_sequence_id(::my_mesh_interfaces::msg::MeshMap & msg)
  : msg_(msg)
  {}
  Init_MeshMap_transmission_stamp sequence_id(::my_mesh_interfaces::msg::MeshMap::_sequence_id_type arg)
  {
    msg_.sequence_id = std::move(arg);
    return Init_MeshMap_transmission_stamp(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshMap msg_;
};

class Init_MeshMap_session_id
{
public:
  Init_MeshMap_session_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_MeshMap_sequence_id session_id(::my_mesh_interfaces::msg::MeshMap::_session_id_type arg)
  {
    msg_.session_id = std::move(arg);
    return Init_MeshMap_sequence_id(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshMap msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::my_mesh_interfaces::msg::MeshMap>()
{
  return my_mesh_interfaces::msg::builder::Init_MeshMap_session_id();
}

}  // namespace my_mesh_interfaces

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__MESH_MAP__BUILDER_HPP_
