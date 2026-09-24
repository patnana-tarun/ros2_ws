// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from my_mesh_interfaces:msg/MeshMap.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/mesh_map.h"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__MESH_MAP__FUNCTIONS_H_
#define MY_MESH_INTERFACES__MSG__DETAIL__MESH_MAP__FUNCTIONS_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdlib.h>

#include "rosidl_runtime_c/action_type_support_struct.h"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_runtime_c/service_type_support_struct.h"
#include "rosidl_runtime_c/type_description/type_description__struct.h"
#include "rosidl_runtime_c/type_description/type_source__struct.h"
#include "rosidl_runtime_c/type_hash.h"
#include "rosidl_runtime_c/visibility_control.h"
#include "my_mesh_interfaces/msg/rosidl_generator_c__visibility_control.h"

#include "my_mesh_interfaces/msg/detail/mesh_map__struct.h"

/// Initialize msg/MeshMap message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * my_mesh_interfaces__msg__MeshMap
 * )) before or use
 * my_mesh_interfaces__msg__MeshMap__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
bool
my_mesh_interfaces__msg__MeshMap__init(my_mesh_interfaces__msg__MeshMap * msg);

/// Finalize msg/MeshMap message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
void
my_mesh_interfaces__msg__MeshMap__fini(my_mesh_interfaces__msg__MeshMap * msg);

/// Create msg/MeshMap message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * my_mesh_interfaces__msg__MeshMap__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
my_mesh_interfaces__msg__MeshMap *
my_mesh_interfaces__msg__MeshMap__create(void);

/// Destroy msg/MeshMap message.
/**
 * It calls
 * my_mesh_interfaces__msg__MeshMap__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
void
my_mesh_interfaces__msg__MeshMap__destroy(my_mesh_interfaces__msg__MeshMap * msg);

/// Check for msg/MeshMap message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
bool
my_mesh_interfaces__msg__MeshMap__are_equal(const my_mesh_interfaces__msg__MeshMap * lhs, const my_mesh_interfaces__msg__MeshMap * rhs);

/// Copy a msg/MeshMap message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
bool
my_mesh_interfaces__msg__MeshMap__copy(
  const my_mesh_interfaces__msg__MeshMap * input,
  my_mesh_interfaces__msg__MeshMap * output);

/// Retrieve pointer to the hash of the description of this type.
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
const rosidl_type_hash_t *
my_mesh_interfaces__msg__MeshMap__get_type_hash(
  const rosidl_message_type_support_t * type_support);

/// Retrieve pointer to the description of this type.
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
const rosidl_runtime_c__type_description__TypeDescription *
my_mesh_interfaces__msg__MeshMap__get_type_description(
  const rosidl_message_type_support_t * type_support);

/// Retrieve pointer to the single raw source text that defined this type.
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
const rosidl_runtime_c__type_description__TypeSource *
my_mesh_interfaces__msg__MeshMap__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support);

/// Retrieve pointer to the recursive raw sources that defined the description of this type.
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
const rosidl_runtime_c__type_description__TypeSource__Sequence *
my_mesh_interfaces__msg__MeshMap__get_type_description_sources(
  const rosidl_message_type_support_t * type_support);

/// Initialize array of msg/MeshMap messages.
/**
 * It allocates the memory for the number of elements and calls
 * my_mesh_interfaces__msg__MeshMap__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
bool
my_mesh_interfaces__msg__MeshMap__Sequence__init(my_mesh_interfaces__msg__MeshMap__Sequence * array, size_t size);

/// Finalize array of msg/MeshMap messages.
/**
 * It calls
 * my_mesh_interfaces__msg__MeshMap__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
void
my_mesh_interfaces__msg__MeshMap__Sequence__fini(my_mesh_interfaces__msg__MeshMap__Sequence * array);

/// Create array of msg/MeshMap messages.
/**
 * It allocates the memory for the array and calls
 * my_mesh_interfaces__msg__MeshMap__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
my_mesh_interfaces__msg__MeshMap__Sequence *
my_mesh_interfaces__msg__MeshMap__Sequence__create(size_t size);

/// Destroy array of msg/MeshMap messages.
/**
 * It calls
 * my_mesh_interfaces__msg__MeshMap__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
void
my_mesh_interfaces__msg__MeshMap__Sequence__destroy(my_mesh_interfaces__msg__MeshMap__Sequence * array);

/// Check for msg/MeshMap message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
bool
my_mesh_interfaces__msg__MeshMap__Sequence__are_equal(const my_mesh_interfaces__msg__MeshMap__Sequence * lhs, const my_mesh_interfaces__msg__MeshMap__Sequence * rhs);

/// Copy an array of msg/MeshMap messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
bool
my_mesh_interfaces__msg__MeshMap__Sequence__copy(
  const my_mesh_interfaces__msg__MeshMap__Sequence * input,
  my_mesh_interfaces__msg__MeshMap__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__MESH_MAP__FUNCTIONS_H_
