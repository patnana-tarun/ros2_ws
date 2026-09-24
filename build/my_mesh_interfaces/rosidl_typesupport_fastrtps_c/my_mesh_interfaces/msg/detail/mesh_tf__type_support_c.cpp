// generated from rosidl_typesupport_fastrtps_c/resource/idl__type_support_c.cpp.em
// with input from my_mesh_interfaces:msg/MeshTf.idl
// generated code does not contain a copyright notice
#include "my_mesh_interfaces/msg/detail/mesh_tf__rosidl_typesupport_fastrtps_c.h"


#include <cassert>
#include <cstddef>
#include <limits>
#include <string>
#include "rosidl_typesupport_fastrtps_c/identifier.h"
#include "rosidl_typesupport_fastrtps_c/serialization_helpers.hpp"
#include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "my_mesh_interfaces/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "my_mesh_interfaces/msg/detail/mesh_tf__struct.h"
#include "my_mesh_interfaces/msg/detail/mesh_tf__functions.h"
#include "fastcdr/Cdr.h"

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

// includes and forward declarations of message dependencies and their conversion functions

#if defined(__cplusplus)
extern "C"
{
#endif

#include "builtin_interfaces/msg/detail/time__functions.h"  // transmission_stamp
#include "tf2_msgs/msg/detail/tf_message__functions.h"  // tf_data

// forward declare type support functions

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
bool cdr_serialize_builtin_interfaces__msg__Time(
  const builtin_interfaces__msg__Time * ros_message,
  eprosima::fastcdr::Cdr & cdr);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
bool cdr_deserialize_builtin_interfaces__msg__Time(
  eprosima::fastcdr::Cdr & cdr,
  builtin_interfaces__msg__Time * ros_message);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
size_t get_serialized_size_builtin_interfaces__msg__Time(
  const void * untyped_ros_message,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
size_t max_serialized_size_builtin_interfaces__msg__Time(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
bool cdr_serialize_key_builtin_interfaces__msg__Time(
  const builtin_interfaces__msg__Time * ros_message,
  eprosima::fastcdr::Cdr & cdr);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
size_t get_serialized_size_key_builtin_interfaces__msg__Time(
  const void * untyped_ros_message,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
size_t max_serialized_size_key_builtin_interfaces__msg__Time(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
const rosidl_message_type_support_t *
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, builtin_interfaces, msg, Time)();

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
bool cdr_serialize_tf2_msgs__msg__TFMessage(
  const tf2_msgs__msg__TFMessage * ros_message,
  eprosima::fastcdr::Cdr & cdr);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
bool cdr_deserialize_tf2_msgs__msg__TFMessage(
  eprosima::fastcdr::Cdr & cdr,
  tf2_msgs__msg__TFMessage * ros_message);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
size_t get_serialized_size_tf2_msgs__msg__TFMessage(
  const void * untyped_ros_message,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
size_t max_serialized_size_tf2_msgs__msg__TFMessage(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
bool cdr_serialize_key_tf2_msgs__msg__TFMessage(
  const tf2_msgs__msg__TFMessage * ros_message,
  eprosima::fastcdr::Cdr & cdr);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
size_t get_serialized_size_key_tf2_msgs__msg__TFMessage(
  const void * untyped_ros_message,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
size_t max_serialized_size_key_tf2_msgs__msg__TFMessage(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

ROSIDL_TYPESUPPORT_FASTRTPS_C_IMPORT_my_mesh_interfaces
const rosidl_message_type_support_t *
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, tf2_msgs, msg, TFMessage)();


using _MeshTf__ros_msg_type = my_mesh_interfaces__msg__MeshTf;


ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_my_mesh_interfaces
bool cdr_serialize_my_mesh_interfaces__msg__MeshTf(
  const my_mesh_interfaces__msg__MeshTf * ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Field name: session_id
  {
    cdr << ros_message->session_id;
  }

  // Field name: sequence_id
  {
    cdr << ros_message->sequence_id;
  }

  // Field name: transmission_stamp
  {
    cdr_serialize_builtin_interfaces__msg__Time(
      &ros_message->transmission_stamp, cdr);
  }

  // Field name: tf_data
  {
    cdr_serialize_tf2_msgs__msg__TFMessage(
      &ros_message->tf_data, cdr);
  }

  // Field name: map_in_flight
  {
    cdr << (ros_message->map_in_flight ? true : false);
  }

  return true;
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_my_mesh_interfaces
bool cdr_deserialize_my_mesh_interfaces__msg__MeshTf(
  eprosima::fastcdr::Cdr & cdr,
  my_mesh_interfaces__msg__MeshTf * ros_message)
{
  // Field name: session_id
  {
    cdr >> ros_message->session_id;
  }

  // Field name: sequence_id
  {
    cdr >> ros_message->sequence_id;
  }

  // Field name: transmission_stamp
  {
    cdr_deserialize_builtin_interfaces__msg__Time(cdr, &ros_message->transmission_stamp);
  }

  // Field name: tf_data
  {
    cdr_deserialize_tf2_msgs__msg__TFMessage(cdr, &ros_message->tf_data);
  }

  // Field name: map_in_flight
  {
    uint8_t tmp;
    cdr >> tmp;
    ros_message->map_in_flight = tmp ? true : false;
  }

  return true;
}  // NOLINT(readability/fn_size)


ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_my_mesh_interfaces
size_t get_serialized_size_my_mesh_interfaces__msg__MeshTf(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _MeshTf__ros_msg_type * ros_message = static_cast<const _MeshTf__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Field name: session_id
  {
    size_t item_size = sizeof(ros_message->session_id);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  // Field name: sequence_id
  {
    size_t item_size = sizeof(ros_message->sequence_id);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  // Field name: transmission_stamp
  current_alignment += get_serialized_size_builtin_interfaces__msg__Time(
    &(ros_message->transmission_stamp), current_alignment);

  // Field name: tf_data
  current_alignment += get_serialized_size_tf2_msgs__msg__TFMessage(
    &(ros_message->tf_data), current_alignment);

  // Field name: map_in_flight
  {
    size_t item_size = sizeof(ros_message->map_in_flight);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}


ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_my_mesh_interfaces
size_t max_serialized_size_my_mesh_interfaces__msg__MeshTf(
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

  // Field name: session_id
  {
    size_t array_size = 1;
    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Field name: sequence_id
  {
    size_t array_size = 1;
    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Field name: transmission_stamp
  {
    size_t array_size = 1;
    last_member_size = 0;
    for (size_t index = 0; index < array_size; ++index) {
      bool inner_full_bounded;
      bool inner_is_plain;
      size_t inner_size;
      inner_size =
        max_serialized_size_builtin_interfaces__msg__Time(
        inner_full_bounded, inner_is_plain, current_alignment);
      last_member_size += inner_size;
      current_alignment += inner_size;
      full_bounded &= inner_full_bounded;
      is_plain &= inner_is_plain;
    }
  }

  // Field name: tf_data
  {
    size_t array_size = 1;
    last_member_size = 0;
    for (size_t index = 0; index < array_size; ++index) {
      bool inner_full_bounded;
      bool inner_is_plain;
      size_t inner_size;
      inner_size =
        max_serialized_size_tf2_msgs__msg__TFMessage(
        inner_full_bounded, inner_is_plain, current_alignment);
      last_member_size += inner_size;
      current_alignment += inner_size;
      full_bounded &= inner_full_bounded;
      is_plain &= inner_is_plain;
    }
  }

  // Field name: map_in_flight
  {
    size_t array_size = 1;
    last_member_size = array_size * sizeof(uint8_t);
    current_alignment += array_size * sizeof(uint8_t);
  }


  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = my_mesh_interfaces__msg__MeshTf;
    is_plain =
      (
      offsetof(DataType, map_in_flight) +
      last_member_size
      ) == ret_val;
  }
  return ret_val;
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_my_mesh_interfaces
bool cdr_serialize_key_my_mesh_interfaces__msg__MeshTf(
  const my_mesh_interfaces__msg__MeshTf * ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Field name: session_id
  {
    cdr << ros_message->session_id;
  }

  // Field name: sequence_id
  {
    cdr << ros_message->sequence_id;
  }

  // Field name: transmission_stamp
  {
    cdr_serialize_key_builtin_interfaces__msg__Time(
      &ros_message->transmission_stamp, cdr);
  }

  // Field name: tf_data
  {
    cdr_serialize_key_tf2_msgs__msg__TFMessage(
      &ros_message->tf_data, cdr);
  }

  // Field name: map_in_flight
  {
    cdr << (ros_message->map_in_flight ? true : false);
  }

  return true;
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_my_mesh_interfaces
size_t get_serialized_size_key_my_mesh_interfaces__msg__MeshTf(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _MeshTf__ros_msg_type * ros_message = static_cast<const _MeshTf__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;

  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Field name: session_id
  {
    size_t item_size = sizeof(ros_message->session_id);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  // Field name: sequence_id
  {
    size_t item_size = sizeof(ros_message->sequence_id);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  // Field name: transmission_stamp
  current_alignment += get_serialized_size_key_builtin_interfaces__msg__Time(
    &(ros_message->transmission_stamp), current_alignment);

  // Field name: tf_data
  current_alignment += get_serialized_size_key_tf2_msgs__msg__TFMessage(
    &(ros_message->tf_data), current_alignment);

  // Field name: map_in_flight
  {
    size_t item_size = sizeof(ros_message->map_in_flight);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_my_mesh_interfaces
size_t max_serialized_size_key_my_mesh_interfaces__msg__MeshTf(
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
  // Field name: session_id
  {
    size_t array_size = 1;
    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Field name: sequence_id
  {
    size_t array_size = 1;
    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Field name: transmission_stamp
  {
    size_t array_size = 1;
    last_member_size = 0;
    for (size_t index = 0; index < array_size; ++index) {
      bool inner_full_bounded;
      bool inner_is_plain;
      size_t inner_size;
      inner_size =
        max_serialized_size_key_builtin_interfaces__msg__Time(
        inner_full_bounded, inner_is_plain, current_alignment);
      last_member_size += inner_size;
      current_alignment += inner_size;
      full_bounded &= inner_full_bounded;
      is_plain &= inner_is_plain;
    }
  }

  // Field name: tf_data
  {
    size_t array_size = 1;
    last_member_size = 0;
    for (size_t index = 0; index < array_size; ++index) {
      bool inner_full_bounded;
      bool inner_is_plain;
      size_t inner_size;
      inner_size =
        max_serialized_size_key_tf2_msgs__msg__TFMessage(
        inner_full_bounded, inner_is_plain, current_alignment);
      last_member_size += inner_size;
      current_alignment += inner_size;
      full_bounded &= inner_full_bounded;
      is_plain &= inner_is_plain;
    }
  }

  // Field name: map_in_flight
  {
    size_t array_size = 1;
    last_member_size = array_size * sizeof(uint8_t);
    current_alignment += array_size * sizeof(uint8_t);
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = my_mesh_interfaces__msg__MeshTf;
    is_plain =
      (
      offsetof(DataType, map_in_flight) +
      last_member_size
      ) == ret_val;
  }
  return ret_val;
}


static bool _MeshTf__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const my_mesh_interfaces__msg__MeshTf * ros_message = static_cast<const my_mesh_interfaces__msg__MeshTf *>(untyped_ros_message);
  (void)ros_message;
  return cdr_serialize_my_mesh_interfaces__msg__MeshTf(ros_message, cdr);
}

static bool _MeshTf__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  my_mesh_interfaces__msg__MeshTf * ros_message = static_cast<my_mesh_interfaces__msg__MeshTf *>(untyped_ros_message);
  (void)ros_message;
  return cdr_deserialize_my_mesh_interfaces__msg__MeshTf(cdr, ros_message);
}

static uint32_t _MeshTf__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_my_mesh_interfaces__msg__MeshTf(
      untyped_ros_message, 0));
}

static size_t _MeshTf__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_my_mesh_interfaces__msg__MeshTf(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_MeshTf = {
  "my_mesh_interfaces::msg",
  "MeshTf",
  _MeshTf__cdr_serialize,
  _MeshTf__cdr_deserialize,
  _MeshTf__get_serialized_size,
  _MeshTf__max_serialized_size,
  nullptr
};

static rosidl_message_type_support_t _MeshTf__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_MeshTf,
  get_message_typesupport_handle_function,
  &my_mesh_interfaces__msg__MeshTf__get_type_hash,
  &my_mesh_interfaces__msg__MeshTf__get_type_description,
  &my_mesh_interfaces__msg__MeshTf__get_type_description_sources,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, my_mesh_interfaces, msg, MeshTf)() {
  return &_MeshTf__type_support;
}

#if defined(__cplusplus)
}
#endif
