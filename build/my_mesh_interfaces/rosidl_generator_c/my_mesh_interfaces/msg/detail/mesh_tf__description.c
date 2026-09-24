// generated from rosidl_generator_c/resource/idl__description.c.em
// with input from my_mesh_interfaces:msg/MeshTf.idl
// generated code does not contain a copyright notice

#include "my_mesh_interfaces/msg/detail/mesh_tf__functions.h"

ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
const rosidl_type_hash_t *
my_mesh_interfaces__msg__MeshTf__get_type_hash(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_type_hash_t hash = {1, {
      0x5e, 0x16, 0xaa, 0xdc, 0xe0, 0x81, 0x77, 0xcc,
      0xe4, 0x8a, 0xa9, 0x43, 0x50, 0xa6, 0x61, 0xe7,
      0x18, 0xa9, 0x32, 0xc5, 0x1d, 0xed, 0xc6, 0x4b,
      0xae, 0x27, 0x6e, 0xab, 0x5f, 0x81, 0xd4, 0x98,
    }};
  return &hash;
}

#include <assert.h>
#include <string.h>

// Include directives for referenced types
#include "geometry_msgs/msg/detail/transform__functions.h"
#include "std_msgs/msg/detail/header__functions.h"
#include "geometry_msgs/msg/detail/transform_stamped__functions.h"
#include "geometry_msgs/msg/detail/vector3__functions.h"
#include "builtin_interfaces/msg/detail/time__functions.h"
#include "tf2_msgs/msg/detail/tf_message__functions.h"
#include "geometry_msgs/msg/detail/quaternion__functions.h"

// Hashes for external referenced types
#ifndef NDEBUG
static const rosidl_type_hash_t builtin_interfaces__msg__Time__EXPECTED_HASH = {1, {
    0xb1, 0x06, 0x23, 0x5e, 0x25, 0xa4, 0xc5, 0xed,
    0x35, 0x09, 0x8a, 0xa0, 0xa6, 0x1a, 0x3e, 0xe9,
    0xc9, 0xb1, 0x8d, 0x19, 0x7f, 0x39, 0x8b, 0x0e,
    0x42, 0x06, 0xce, 0xa9, 0xac, 0xf9, 0xc1, 0x97,
  }};
static const rosidl_type_hash_t geometry_msgs__msg__Quaternion__EXPECTED_HASH = {1, {
    0x8a, 0x76, 0x5f, 0x66, 0x77, 0x8c, 0x8f, 0xf7,
    0xc8, 0xab, 0x94, 0xaf, 0xcc, 0x59, 0x0a, 0x2e,
    0xd5, 0x32, 0x5a, 0x1d, 0x9a, 0x07, 0x6f, 0xff,
    0xf3, 0x8f, 0xbc, 0xe3, 0x6f, 0x45, 0x86, 0x84,
  }};
static const rosidl_type_hash_t geometry_msgs__msg__Transform__EXPECTED_HASH = {1, {
    0xbe, 0xb8, 0x3f, 0xbe, 0x69, 0x86, 0x36, 0x35,
    0x14, 0x61, 0xf6, 0xf3, 0x5d, 0x1a, 0xbb, 0x20,
    0x01, 0x0c, 0x43, 0xd5, 0x53, 0x74, 0xd8, 0x1b,
    0xd0, 0x41, 0xf1, 0xba, 0x25, 0x81, 0xfd, 0xdc,
  }};
static const rosidl_type_hash_t geometry_msgs__msg__TransformStamped__EXPECTED_HASH = {1, {
    0x0a, 0x24, 0x1f, 0x87, 0xd0, 0x46, 0x68, 0xd9,
    0x40, 0x99, 0xcb, 0xb5, 0xba, 0x11, 0x69, 0x1d,
    0x5a, 0xd3, 0x2c, 0x2f, 0x29, 0x68, 0x2e, 0x4e,
    0xb5, 0x65, 0x34, 0x24, 0xbd, 0x27, 0x52, 0x06,
  }};
static const rosidl_type_hash_t geometry_msgs__msg__Vector3__EXPECTED_HASH = {1, {
    0xcc, 0x12, 0xfe, 0x83, 0xe4, 0xc0, 0x27, 0x19,
    0xf1, 0xce, 0x80, 0x70, 0xbf, 0xd1, 0x4a, 0xec,
    0xd4, 0x0f, 0x75, 0xa9, 0x66, 0x96, 0xa6, 0x7a,
    0x2a, 0x1f, 0x37, 0xf7, 0xdb, 0xb0, 0x76, 0x5d,
  }};
static const rosidl_type_hash_t std_msgs__msg__Header__EXPECTED_HASH = {1, {
    0xf4, 0x9f, 0xb3, 0xae, 0x2c, 0xf0, 0x70, 0xf7,
    0x93, 0x64, 0x5f, 0xf7, 0x49, 0x68, 0x3a, 0xc6,
    0xb0, 0x62, 0x03, 0xe4, 0x1c, 0x89, 0x1e, 0x17,
    0x70, 0x1b, 0x1c, 0xb5, 0x97, 0xce, 0x6a, 0x01,
  }};
static const rosidl_type_hash_t tf2_msgs__msg__TFMessage__EXPECTED_HASH = {1, {
    0xe3, 0x69, 0xd0, 0xf0, 0x5a, 0x23, 0xae, 0x52,
    0x50, 0x88, 0x54, 0xb6, 0x6f, 0x6a, 0xa0, 0x43,
    0x7f, 0x34, 0x49, 0xd6, 0x52, 0xe8, 0xcb, 0xf2,
    0x2d, 0x5a, 0xbe, 0x85, 0xd0, 0x20, 0xf0, 0x87,
  }};
#endif

static char my_mesh_interfaces__msg__MeshTf__TYPE_NAME[] = "my_mesh_interfaces/msg/MeshTf";
static char builtin_interfaces__msg__Time__TYPE_NAME[] = "builtin_interfaces/msg/Time";
static char geometry_msgs__msg__Quaternion__TYPE_NAME[] = "geometry_msgs/msg/Quaternion";
static char geometry_msgs__msg__Transform__TYPE_NAME[] = "geometry_msgs/msg/Transform";
static char geometry_msgs__msg__TransformStamped__TYPE_NAME[] = "geometry_msgs/msg/TransformStamped";
static char geometry_msgs__msg__Vector3__TYPE_NAME[] = "geometry_msgs/msg/Vector3";
static char std_msgs__msg__Header__TYPE_NAME[] = "std_msgs/msg/Header";
static char tf2_msgs__msg__TFMessage__TYPE_NAME[] = "tf2_msgs/msg/TFMessage";

// Define type names, field names, and default values
static char my_mesh_interfaces__msg__MeshTf__FIELD_NAME__session_id[] = "session_id";
static char my_mesh_interfaces__msg__MeshTf__FIELD_NAME__sequence_id[] = "sequence_id";
static char my_mesh_interfaces__msg__MeshTf__FIELD_NAME__transmission_stamp[] = "transmission_stamp";
static char my_mesh_interfaces__msg__MeshTf__FIELD_NAME__tf_data[] = "tf_data";
static char my_mesh_interfaces__msg__MeshTf__FIELD_NAME__map_in_flight[] = "map_in_flight";

static rosidl_runtime_c__type_description__Field my_mesh_interfaces__msg__MeshTf__FIELDS[] = {
  {
    {my_mesh_interfaces__msg__MeshTf__FIELD_NAME__session_id, 10, 10},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_UINT64,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
  {
    {my_mesh_interfaces__msg__MeshTf__FIELD_NAME__sequence_id, 11, 11},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_UINT64,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
  {
    {my_mesh_interfaces__msg__MeshTf__FIELD_NAME__transmission_stamp, 18, 18},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {builtin_interfaces__msg__Time__TYPE_NAME, 27, 27},
    },
    {NULL, 0, 0},
  },
  {
    {my_mesh_interfaces__msg__MeshTf__FIELD_NAME__tf_data, 7, 7},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {tf2_msgs__msg__TFMessage__TYPE_NAME, 22, 22},
    },
    {NULL, 0, 0},
  },
  {
    {my_mesh_interfaces__msg__MeshTf__FIELD_NAME__map_in_flight, 13, 13},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_BOOLEAN,
      0,
      0,
      {NULL, 0, 0},
    },
    {NULL, 0, 0},
  },
};

static rosidl_runtime_c__type_description__IndividualTypeDescription my_mesh_interfaces__msg__MeshTf__REFERENCED_TYPE_DESCRIPTIONS[] = {
  {
    {builtin_interfaces__msg__Time__TYPE_NAME, 27, 27},
    {NULL, 0, 0},
  },
  {
    {geometry_msgs__msg__Quaternion__TYPE_NAME, 28, 28},
    {NULL, 0, 0},
  },
  {
    {geometry_msgs__msg__Transform__TYPE_NAME, 27, 27},
    {NULL, 0, 0},
  },
  {
    {geometry_msgs__msg__TransformStamped__TYPE_NAME, 34, 34},
    {NULL, 0, 0},
  },
  {
    {geometry_msgs__msg__Vector3__TYPE_NAME, 25, 25},
    {NULL, 0, 0},
  },
  {
    {std_msgs__msg__Header__TYPE_NAME, 19, 19},
    {NULL, 0, 0},
  },
  {
    {tf2_msgs__msg__TFMessage__TYPE_NAME, 22, 22},
    {NULL, 0, 0},
  },
};

const rosidl_runtime_c__type_description__TypeDescription *
my_mesh_interfaces__msg__MeshTf__get_type_description(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static bool constructed = false;
  static const rosidl_runtime_c__type_description__TypeDescription description = {
    {
      {my_mesh_interfaces__msg__MeshTf__TYPE_NAME, 29, 29},
      {my_mesh_interfaces__msg__MeshTf__FIELDS, 5, 5},
    },
    {my_mesh_interfaces__msg__MeshTf__REFERENCED_TYPE_DESCRIPTIONS, 7, 7},
  };
  if (!constructed) {
    assert(0 == memcmp(&builtin_interfaces__msg__Time__EXPECTED_HASH, builtin_interfaces__msg__Time__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[0].fields = builtin_interfaces__msg__Time__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&geometry_msgs__msg__Quaternion__EXPECTED_HASH, geometry_msgs__msg__Quaternion__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[1].fields = geometry_msgs__msg__Quaternion__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&geometry_msgs__msg__Transform__EXPECTED_HASH, geometry_msgs__msg__Transform__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[2].fields = geometry_msgs__msg__Transform__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&geometry_msgs__msg__TransformStamped__EXPECTED_HASH, geometry_msgs__msg__TransformStamped__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[3].fields = geometry_msgs__msg__TransformStamped__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&geometry_msgs__msg__Vector3__EXPECTED_HASH, geometry_msgs__msg__Vector3__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[4].fields = geometry_msgs__msg__Vector3__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&std_msgs__msg__Header__EXPECTED_HASH, std_msgs__msg__Header__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[5].fields = std_msgs__msg__Header__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&tf2_msgs__msg__TFMessage__EXPECTED_HASH, tf2_msgs__msg__TFMessage__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[6].fields = tf2_msgs__msg__TFMessage__get_type_description(NULL)->type_description.fields;
    constructed = true;
  }
  return &description;
}

static char toplevel_type_raw_source[] =
  "uint64 session_id\n"
  "uint64 sequence_id\n"
  "builtin_interfaces/Time transmission_stamp\n"
  "tf2_msgs/TFMessage tf_data\n"
  "bool map_in_flight";

static char msg_encoding[] = "msg";

// Define all individual source functions

const rosidl_runtime_c__type_description__TypeSource *
my_mesh_interfaces__msg__MeshTf__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static const rosidl_runtime_c__type_description__TypeSource source = {
    {my_mesh_interfaces__msg__MeshTf__TYPE_NAME, 29, 29},
    {msg_encoding, 3, 3},
    {toplevel_type_raw_source, 126, 126},
  };
  return &source;
}

const rosidl_runtime_c__type_description__TypeSource__Sequence *
my_mesh_interfaces__msg__MeshTf__get_type_description_sources(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_runtime_c__type_description__TypeSource sources[8];
  static const rosidl_runtime_c__type_description__TypeSource__Sequence source_sequence = {sources, 8, 8};
  static bool constructed = false;
  if (!constructed) {
    sources[0] = *my_mesh_interfaces__msg__MeshTf__get_individual_type_description_source(NULL),
    sources[1] = *builtin_interfaces__msg__Time__get_individual_type_description_source(NULL);
    sources[2] = *geometry_msgs__msg__Quaternion__get_individual_type_description_source(NULL);
    sources[3] = *geometry_msgs__msg__Transform__get_individual_type_description_source(NULL);
    sources[4] = *geometry_msgs__msg__TransformStamped__get_individual_type_description_source(NULL);
    sources[5] = *geometry_msgs__msg__Vector3__get_individual_type_description_source(NULL);
    sources[6] = *std_msgs__msg__Header__get_individual_type_description_source(NULL);
    sources[7] = *tf2_msgs__msg__TFMessage__get_individual_type_description_source(NULL);
    constructed = true;
  }
  return &source_sequence;
}
