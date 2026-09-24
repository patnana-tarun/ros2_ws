// generated from rosidl_typesupport_introspection_cpp/resource/idl__type_support.cpp.em
// with input from my_mesh_interfaces:msg/SenderStatus.idl
// generated code does not contain a copyright notice

#include "array"
#include "cstddef"
#include "string"
#include "vector"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_interface/macros.h"
#include "my_mesh_interfaces/msg/detail/sender_status__functions.h"
#include "my_mesh_interfaces/msg/detail/sender_status__struct.hpp"
#include "rosidl_typesupport_introspection_cpp/field_types.hpp"
#include "rosidl_typesupport_introspection_cpp/identifier.hpp"
#include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace my_mesh_interfaces
{

namespace msg
{

namespace rosidl_typesupport_introspection_cpp
{

void SenderStatus_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) my_mesh_interfaces::msg::SenderStatus(_init);
}

void SenderStatus_fini_function(void * message_memory)
{
  auto typed_message = static_cast<my_mesh_interfaces::msg::SenderStatus *>(message_memory);
  typed_message->~SenderStatus();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember SenderStatus_message_member_array[2] = {
  {
    "session_id",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_UINT64,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is key
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(my_mesh_interfaces::msg::SenderStatus, session_id),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  },
  {
    "last_sequence_sent",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_UINT64,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is key
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(my_mesh_interfaces::msg::SenderStatus, last_sequence_sent),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers SenderStatus_message_members = {
  "my_mesh_interfaces::msg",  // message namespace
  "SenderStatus",  // message name
  2,  // number of fields
  sizeof(my_mesh_interfaces::msg::SenderStatus),
  false,  // has_any_key_member_
  SenderStatus_message_member_array,  // message members
  SenderStatus_init_function,  // function to initialize message memory (memory has to be allocated)
  SenderStatus_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t SenderStatus_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &SenderStatus_message_members,
  get_message_typesupport_handle_function,
  &my_mesh_interfaces__msg__SenderStatus__get_type_hash,
  &my_mesh_interfaces__msg__SenderStatus__get_type_description,
  &my_mesh_interfaces__msg__SenderStatus__get_type_description_sources,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace msg

}  // namespace my_mesh_interfaces


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<my_mesh_interfaces::msg::SenderStatus>()
{
  return &::my_mesh_interfaces::msg::rosidl_typesupport_introspection_cpp::SenderStatus_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, my_mesh_interfaces, msg, SenderStatus)() {
  return &::my_mesh_interfaces::msg::rosidl_typesupport_introspection_cpp::SenderStatus_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif
