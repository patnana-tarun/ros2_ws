// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from my_mesh_interfaces:msg/SenderStatus.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/sender_status.hpp"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__BUILDER_HPP_
#define MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "my_mesh_interfaces/msg/detail/sender_status__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace my_mesh_interfaces
{

namespace msg
{

namespace builder
{

class Init_SenderStatus_last_sequence_sent
{
public:
  explicit Init_SenderStatus_last_sequence_sent(::my_mesh_interfaces::msg::SenderStatus & msg)
  : msg_(msg)
  {}
  ::my_mesh_interfaces::msg::SenderStatus last_sequence_sent(::my_mesh_interfaces::msg::SenderStatus::_last_sequence_sent_type arg)
  {
    msg_.last_sequence_sent = std::move(arg);
    return std::move(msg_);
  }

private:
  ::my_mesh_interfaces::msg::SenderStatus msg_;
};

class Init_SenderStatus_session_id
{
public:
  Init_SenderStatus_session_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_SenderStatus_last_sequence_sent session_id(::my_mesh_interfaces::msg::SenderStatus::_session_id_type arg)
  {
    msg_.session_id = std::move(arg);
    return Init_SenderStatus_last_sequence_sent(msg_);
  }

private:
  ::my_mesh_interfaces::msg::SenderStatus msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::my_mesh_interfaces::msg::SenderStatus>()
{
  return my_mesh_interfaces::msg::builder::Init_SenderStatus_session_id();
}

}  // namespace my_mesh_interfaces

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__BUILDER_HPP_
