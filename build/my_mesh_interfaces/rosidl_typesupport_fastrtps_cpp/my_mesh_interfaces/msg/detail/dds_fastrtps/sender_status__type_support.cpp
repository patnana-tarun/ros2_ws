// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__type_support.cpp.em
// with input from my_mesh_interfaces:msg/SenderStatus.idl
// generated code does not contain a copyright notice
#include "my_mesh_interfaces/msg/detail/sender_status__rosidl_typesupport_fastrtps_cpp.hpp"
#include "my_mesh_interfaces/msg/detail/sender_status__functions.h"
#include "my_mesh_interfaces/msg/detail/sender_status__struct.hpp"

#include <cstddef>
#include <limits>
#include <stdexcept>
#include <string>
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_fastrtps_cpp/identifier.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_fastrtps_cpp/serialization_helpers.hpp"
#include "rosidl_typesupport_fastrtps_cpp/wstring_conversion.hpp"
#include "fastcdr/Cdr.h"


// forward declaration of message dependencies and their conversion functions

namespace my_mesh_interfaces
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{


bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
cdr_serialize(
  const my_mesh_interfaces::msg::SenderStatus & ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Member: session_id
  cdr << ros_message.session_id;

  // Member: last_sequence_sent
  cdr << ros_message.last_sequence_sent;

  return true;
}

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  my_mesh_interfaces::msg::SenderStatus & ros_message)
{
  // Member: session_id
  cdr >> ros_message.session_id;

  // Member: last_sequence_sent
  cdr >> ros_message.last_sequence_sent;

  return true;
}  // NOLINT(readability/fn_size)


size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
get_serialized_size(
  const my_mesh_interfaces::msg::SenderStatus & ros_message,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Member: session_id
  {
    size_t item_size = sizeof(ros_message.session_id);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  // Member: last_sequence_sent
  {
    size_t item_size = sizeof(ros_message.last_sequence_sent);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}


size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
max_serialized_size_SenderStatus(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  size_t last_member_size = 0;
  (void)last_member_size;
  (void)padding;
  (void)wchar_size;

  full_bounded = true;
  is_plain = true;

  // Member: session_id
  {
    size_t array_size = 1;
    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }
  // Member: last_sequence_sent
  {
    size_t array_size = 1;
    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = my_mesh_interfaces::msg::SenderStatus;
    is_plain =
      (
      offsetof(DataType, last_sequence_sent) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
cdr_serialize_key(
  const my_mesh_interfaces::msg::SenderStatus & ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Member: session_id
  cdr << ros_message.session_id;

  // Member: last_sequence_sent
  cdr << ros_message.last_sequence_sent;

  return true;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
get_serialized_size_key(
  const my_mesh_interfaces::msg::SenderStatus & ros_message,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Member: session_id
  {
    size_t item_size = sizeof(ros_message.session_id);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  // Member: last_sequence_sent
  {
    size_t item_size = sizeof(ros_message.last_sequence_sent);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_my_mesh_interfaces
max_serialized_size_key_SenderStatus(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  size_t last_member_size = 0;
  (void)last_member_size;
  (void)padding;
  (void)wchar_size;

  full_bounded = true;
  is_plain = true;

  // Member: session_id
  {
    size_t array_size = 1;
    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: last_sequence_sent
  {
    size_t array_size = 1;
    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = my_mesh_interfaces::msg::SenderStatus;
    is_plain =
      (
      offsetof(DataType, last_sequence_sent) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}


static bool _SenderStatus__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  auto typed_message =
    static_cast<const my_mesh_interfaces::msg::SenderStatus *>(
    untyped_ros_message);
  return cdr_serialize(*typed_message, cdr);
}

static bool _SenderStatus__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  auto typed_message =
    static_cast<my_mesh_interfaces::msg::SenderStatus *>(
    untyped_ros_message);
  return cdr_deserialize(cdr, *typed_message);
}

static uint32_t _SenderStatus__get_serialized_size(
  const void * untyped_ros_message)
{
  auto typed_message =
    static_cast<const my_mesh_interfaces::msg::SenderStatus *>(
    untyped_ros_message);
  return static_cast<uint32_t>(get_serialized_size(*typed_message, 0));
}

static size_t _SenderStatus__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_SenderStatus(full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}

static message_type_support_callbacks_t _SenderStatus__callbacks = {
  "my_mesh_interfaces::msg",
  "SenderStatus",
  _SenderStatus__cdr_serialize,
  _SenderStatus__cdr_deserialize,
  _SenderStatus__get_serialized_size,
  _SenderStatus__max_serialized_size,
  nullptr
};

static rosidl_message_type_support_t _SenderStatus__handle = {
  rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
  &_SenderStatus__callbacks,
  get_message_typesupport_handle_function,
  &my_mesh_interfaces__msg__SenderStatus__get_type_hash,
  &my_mesh_interfaces__msg__SenderStatus__get_type_description,
  &my_mesh_interfaces__msg__SenderStatus__get_type_description_sources,
};

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace my_mesh_interfaces

namespace rosidl_typesupport_fastrtps_cpp
{

template<>
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_my_mesh_interfaces
const rosidl_message_type_support_t *
get_message_type_support_handle<my_mesh_interfaces::msg::SenderStatus>()
{
  return &my_mesh_interfaces::msg::typesupport_fastrtps_cpp::_SenderStatus__handle;
}

}  // namespace rosidl_typesupport_fastrtps_cpp

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, my_mesh_interfaces, msg, SenderStatus)() {
  return &my_mesh_interfaces::msg::typesupport_fastrtps_cpp::_SenderStatus__handle;
}

#ifdef __cplusplus
}
#endif
