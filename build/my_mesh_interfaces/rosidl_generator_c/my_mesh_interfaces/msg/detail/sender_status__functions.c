// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from my_mesh_interfaces:msg/SenderStatus.idl
// generated code does not contain a copyright notice
#include "my_mesh_interfaces/msg/detail/sender_status__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


bool
my_mesh_interfaces__msg__SenderStatus__init(my_mesh_interfaces__msg__SenderStatus * msg)
{
  if (!msg) {
    return false;
  }
  // session_id
  // last_sequence_sent
  return true;
}

void
my_mesh_interfaces__msg__SenderStatus__fini(my_mesh_interfaces__msg__SenderStatus * msg)
{
  if (!msg) {
    return;
  }
  // session_id
  // last_sequence_sent
}

bool
my_mesh_interfaces__msg__SenderStatus__are_equal(const my_mesh_interfaces__msg__SenderStatus * lhs, const my_mesh_interfaces__msg__SenderStatus * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // session_id
  if (lhs->session_id != rhs->session_id) {
    return false;
  }
  // last_sequence_sent
  if (lhs->last_sequence_sent != rhs->last_sequence_sent) {
    return false;
  }
  return true;
}

bool
my_mesh_interfaces__msg__SenderStatus__copy(
  const my_mesh_interfaces__msg__SenderStatus * input,
  my_mesh_interfaces__msg__SenderStatus * output)
{
  if (!input || !output) {
    return false;
  }
  // session_id
  output->session_id = input->session_id;
  // last_sequence_sent
  output->last_sequence_sent = input->last_sequence_sent;
  return true;
}

my_mesh_interfaces__msg__SenderStatus *
my_mesh_interfaces__msg__SenderStatus__create(void)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  my_mesh_interfaces__msg__SenderStatus * msg = (my_mesh_interfaces__msg__SenderStatus *)allocator.allocate(sizeof(my_mesh_interfaces__msg__SenderStatus), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(my_mesh_interfaces__msg__SenderStatus));
  bool success = my_mesh_interfaces__msg__SenderStatus__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
my_mesh_interfaces__msg__SenderStatus__destroy(my_mesh_interfaces__msg__SenderStatus * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    my_mesh_interfaces__msg__SenderStatus__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
my_mesh_interfaces__msg__SenderStatus__Sequence__init(my_mesh_interfaces__msg__SenderStatus__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  my_mesh_interfaces__msg__SenderStatus * data = NULL;

  if (size) {
    if (size > SIZE_MAX / sizeof(my_mesh_interfaces__msg__SenderStatus)) {
      return false;
    }
    data = (my_mesh_interfaces__msg__SenderStatus *)allocator.zero_allocate(size, sizeof(my_mesh_interfaces__msg__SenderStatus), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = my_mesh_interfaces__msg__SenderStatus__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        my_mesh_interfaces__msg__SenderStatus__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
my_mesh_interfaces__msg__SenderStatus__Sequence__fini(my_mesh_interfaces__msg__SenderStatus__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      my_mesh_interfaces__msg__SenderStatus__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

my_mesh_interfaces__msg__SenderStatus__Sequence *
my_mesh_interfaces__msg__SenderStatus__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  my_mesh_interfaces__msg__SenderStatus__Sequence * array = (my_mesh_interfaces__msg__SenderStatus__Sequence *)allocator.allocate(sizeof(my_mesh_interfaces__msg__SenderStatus__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = my_mesh_interfaces__msg__SenderStatus__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
my_mesh_interfaces__msg__SenderStatus__Sequence__destroy(my_mesh_interfaces__msg__SenderStatus__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    my_mesh_interfaces__msg__SenderStatus__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
my_mesh_interfaces__msg__SenderStatus__Sequence__are_equal(const my_mesh_interfaces__msg__SenderStatus__Sequence * lhs, const my_mesh_interfaces__msg__SenderStatus__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!my_mesh_interfaces__msg__SenderStatus__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
my_mesh_interfaces__msg__SenderStatus__Sequence__copy(
  const my_mesh_interfaces__msg__SenderStatus__Sequence * input,
  my_mesh_interfaces__msg__SenderStatus__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    if (input->size > SIZE_MAX / sizeof(my_mesh_interfaces__msg__SenderStatus)) {
      return false;
    }
    const size_t allocation_size =
      input->size * sizeof(my_mesh_interfaces__msg__SenderStatus);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    my_mesh_interfaces__msg__SenderStatus * data =
      (my_mesh_interfaces__msg__SenderStatus *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!my_mesh_interfaces__msg__SenderStatus__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          my_mesh_interfaces__msg__SenderStatus__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!my_mesh_interfaces__msg__SenderStatus__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
