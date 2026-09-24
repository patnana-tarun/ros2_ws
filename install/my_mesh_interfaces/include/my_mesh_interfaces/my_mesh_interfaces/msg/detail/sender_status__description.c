// generated from rosidl_generator_c/resource/idl__description.c.em
// with input from my_mesh_interfaces:msg/SenderStatus.idl
// generated code does not contain a copyright notice

#include "my_mesh_interfaces/msg/detail/sender_status__functions.h"

ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
const rosidl_type_hash_t *
my_mesh_interfaces__msg__SenderStatus__get_type_hash(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_type_hash_t hash = {1, {
      0xbf, 0xf1, 0x54, 0x5c, 0xcd, 0xd3, 0x03, 0xec,
      0xbe, 0x33, 0xe7, 0x08, 0x3e, 0xfd, 0x0c, 0x61,
      0x10, 0x3b, 0x04, 0xfd, 0xf6, 0xeb, 0x44, 0x09,
      0xe9, 0x1b, 0x5c, 0xa1, 0x16, 0xa0, 0x2b, 0x8f,
    }};
  return &hash;
}

#include <assert.h>
#include <string.h>

// Include directives for referenced types

// Hashes for external referenced types
#ifndef NDEBUG
#endif

static char my_mesh_interfaces__msg__SenderStatus__TYPE_NAME[] = "my_mesh_interfaces/msg/SenderStatus";

// Define type names, field names, and default values
static char my_mesh_interfaces__msg__SenderStatus__FIELD_NAME__session_id[] = "session_id";
static char my_mesh_interfaces__msg__SenderStatus__FIELD_NAME__last_sequence_sent[] = "last_sequence_sent";

static rosidl_runtime_c__type_description__Field my_mesh_interfaces__msg__SenderStatus__FIELDS[] = {
  {
    {my_mesh_interfaces__msg__SenderStatus__FIELD_NAME__session_id, 10, 10},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_UINT64,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
  {
    {my_mesh_interfaces__msg__SenderStatus__FIELD_NAME__last_sequence_sent, 18, 18},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_UINT64,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
};

const rosidl_runtime_c__type_description__TypeDescription *
my_mesh_interfaces__msg__SenderStatus__get_type_description(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static bool constructed = false;
  static const rosidl_runtime_c__type_description__TypeDescription description = {
    {
      {my_mesh_interfaces__msg__SenderStatus__TYPE_NAME, 35, 35},
      {my_mesh_interfaces__msg__SenderStatus__FIELDS, 2, 2},
    },
    {NULL, 0, 0},
  };
  if (!constructed) {
    constructed = true;
  }
  return &description;
}

static char toplevel_type_raw_source[] =
  "uint64 session_id\n"
  "uint64 last_sequence_sent\n"
  "";

static char msg_encoding[] = "msg";

// Define all individual source functions

const rosidl_runtime_c__type_description__TypeSource *
my_mesh_interfaces__msg__SenderStatus__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static const rosidl_runtime_c__type_description__TypeSource source = {
    {my_mesh_interfaces__msg__SenderStatus__TYPE_NAME, 35, 35},
    {msg_encoding, 3, 3},
    {toplevel_type_raw_source, 45, 45},
  };
  return &source;
}

const rosidl_runtime_c__type_description__TypeSource__Sequence *
my_mesh_interfaces__msg__SenderStatus__get_type_description_sources(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_runtime_c__type_description__TypeSource sources[1];
  static const rosidl_runtime_c__type_description__TypeSource__Sequence source_sequence = {sources, 1, 1};
  static bool constructed = false;
  if (!constructed) {
    sources[0] = *my_mesh_interfaces__msg__SenderStatus__get_individual_type_description_source(NULL),
    constructed = true;
  }
  return &source_sequence;
}
