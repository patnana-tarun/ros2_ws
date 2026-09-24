// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from my_mesh_interfaces:msg/SenderStatus.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/sender_status.h"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__FUNCTIONS_H_
#define MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__FUNCTIONS_H_

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

#include "my_mesh_interfaces/msg/detail/sender_status__struct.h"

/// Initialize msg/SenderStatus message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * my_mesh_interfaces__msg__SenderStatus
 * )) before or use
 * my_mesh_interfaces__msg__SenderStatus__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
bool
my_mesh_interfaces__msg__SenderStatus__init(my_mesh_interfaces__msg__SenderStatus * msg);

/// Finalize msg/SenderStatus message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
void
my_mesh_interfaces__msg__SenderStatus__fini(my_mesh_interfaces__msg__SenderStatus * msg);

/// Create msg/SenderStatus message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * my_mesh_interfaces__msg__SenderStatus__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
my_mesh_interfaces__msg__SenderStatus *
my_mesh_interfaces__msg__SenderStatus__create(void);

/// Destroy msg/SenderStatus message.
/**
 * It calls
 * my_mesh_interfaces__msg__SenderStatus__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
void
my_mesh_interfaces__msg__SenderStatus__destroy(my_mesh_interfaces__msg__SenderStatus * msg);

/// Check for msg/SenderStatus message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
bool
my_mesh_interfaces__msg__SenderStatus__are_equal(const my_mesh_interfaces__msg__SenderStatus * lhs, const my_mesh_interfaces__msg__SenderStatus * rhs);

/// Copy a msg/SenderStatus message.
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
my_mesh_interfaces__msg__SenderStatus__copy(
  const my_mesh_interfaces__msg__SenderStatus * input,
  my_mesh_interfaces__msg__SenderStatus * output);

/// Retrieve pointer to the hash of the description of this type.
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
const rosidl_type_hash_t *
my_mesh_interfaces__msg__SenderStatus__get_type_hash(
  const rosidl_message_type_support_t * type_support);

/// Retrieve pointer to the description of this type.
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
const rosidl_runtime_c__type_description__TypeDescription *
my_mesh_interfaces__msg__SenderStatus__get_type_description(
  const rosidl_message_type_support_t * type_support);

/// Retrieve pointer to the single raw source text that defined this type.
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
const rosidl_runtime_c__type_description__TypeSource *
my_mesh_interfaces__msg__SenderStatus__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support);

/// Retrieve pointer to the recursive raw sources that defined the description of this type.
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
const rosidl_runtime_c__type_description__TypeSource__Sequence *
my_mesh_interfaces__msg__SenderStatus__get_type_description_sources(
  const rosidl_message_type_support_t * type_support);

/// Initialize array of msg/SenderStatus messages.
/**
 * It allocates the memory for the number of elements and calls
 * my_mesh_interfaces__msg__SenderStatus__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
bool
my_mesh_interfaces__msg__SenderStatus__Sequence__init(my_mesh_interfaces__msg__SenderStatus__Sequence * array, size_t size);

/// Finalize array of msg/SenderStatus messages.
/**
 * It calls
 * my_mesh_interfaces__msg__SenderStatus__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
void
my_mesh_interfaces__msg__SenderStatus__Sequence__fini(my_mesh_interfaces__msg__SenderStatus__Sequence * array);

/// Create array of msg/SenderStatus messages.
/**
 * It allocates the memory for the array and calls
 * my_mesh_interfaces__msg__SenderStatus__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
my_mesh_interfaces__msg__SenderStatus__Sequence *
my_mesh_interfaces__msg__SenderStatus__Sequence__create(size_t size);

/// Destroy array of msg/SenderStatus messages.
/**
 * It calls
 * my_mesh_interfaces__msg__SenderStatus__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
void
my_mesh_interfaces__msg__SenderStatus__Sequence__destroy(my_mesh_interfaces__msg__SenderStatus__Sequence * array);

/// Check for msg/SenderStatus message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_my_mesh_interfaces
bool
my_mesh_interfaces__msg__SenderStatus__Sequence__are_equal(const my_mesh_interfaces__msg__SenderStatus__Sequence * lhs, const my_mesh_interfaces__msg__SenderStatus__Sequence * rhs);

/// Copy an array of msg/SenderStatus messages.
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
my_mesh_interfaces__msg__SenderStatus__Sequence__copy(
  const my_mesh_interfaces__msg__SenderStatus__Sequence * input,
  my_mesh_interfaces__msg__SenderStatus__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__FUNCTIONS_H_
