// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from my_mesh_interfaces:msg/MeshTf.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/mesh_tf.hpp"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__MESH_TF__BUILDER_HPP_
#define MY_MESH_INTERFACES__MSG__DETAIL__MESH_TF__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "my_mesh_interfaces/msg/detail/mesh_tf__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace my_mesh_interfaces
{

namespace msg
{

namespace builder
{

class Init_MeshTf_map_in_flight
{
public:
  explicit Init_MeshTf_map_in_flight(::my_mesh_interfaces::msg::MeshTf & msg)
  : msg_(msg)
  {}
  ::my_mesh_interfaces::msg::MeshTf map_in_flight(::my_mesh_interfaces::msg::MeshTf::_map_in_flight_type arg)
  {
    msg_.map_in_flight = std::move(arg);
    return std::move(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshTf msg_;
};

class Init_MeshTf_tf_data
{
public:
  explicit Init_MeshTf_tf_data(::my_mesh_interfaces::msg::MeshTf & msg)
  : msg_(msg)
  {}
  Init_MeshTf_map_in_flight tf_data(::my_mesh_interfaces::msg::MeshTf::_tf_data_type arg)
  {
    msg_.tf_data = std::move(arg);
    return Init_MeshTf_map_in_flight(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshTf msg_;
};

class Init_MeshTf_transmission_stamp
{
public:
  explicit Init_MeshTf_transmission_stamp(::my_mesh_interfaces::msg::MeshTf & msg)
  : msg_(msg)
  {}
  Init_MeshTf_tf_data transmission_stamp(::my_mesh_interfaces::msg::MeshTf::_transmission_stamp_type arg)
  {
    msg_.transmission_stamp = std::move(arg);
    return Init_MeshTf_tf_data(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshTf msg_;
};

class Init_MeshTf_sequence_id
{
public:
  explicit Init_MeshTf_sequence_id(::my_mesh_interfaces::msg::MeshTf & msg)
  : msg_(msg)
  {}
  Init_MeshTf_transmission_stamp sequence_id(::my_mesh_interfaces::msg::MeshTf::_sequence_id_type arg)
  {
    msg_.sequence_id = std::move(arg);
    return Init_MeshTf_transmission_stamp(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshTf msg_;
};

class Init_MeshTf_session_id
{
public:
  Init_MeshTf_session_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_MeshTf_sequence_id session_id(::my_mesh_interfaces::msg::MeshTf::_session_id_type arg)
  {
    msg_.session_id = std::move(arg);
    return Init_MeshTf_sequence_id(msg_);
  }

private:
  ::my_mesh_interfaces::msg::MeshTf msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::my_mesh_interfaces::msg::MeshTf>()
{
  return my_mesh_interfaces::msg::builder::Init_MeshTf_session_id();
}

}  // namespace my_mesh_interfaces

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__MESH_TF__BUILDER_HPP_
