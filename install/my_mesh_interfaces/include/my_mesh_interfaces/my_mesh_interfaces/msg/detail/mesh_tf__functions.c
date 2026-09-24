// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from my_mesh_interfaces:msg/MeshTf.idl
// generated code does not contain a copyright notice
#include "my_mesh_interfaces/msg/detail/mesh_tf__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `transmission_stamp`
#include "builtin_interfaces/msg/detail/time__functions.h"
// Member `tf_data`
#include "tf2_msgs/msg/detail/tf_message__functions.h"

bool
my_mesh_interfaces__msg__MeshTf__init(my_mesh_interfaces__msg__MeshTf * msg)
{
  if (!msg) {
    return false;
  }
  // session_id
  // sequence_id
  // transmission_stamp
  if (!builtin_interfaces__msg__Time__init(&msg->transmission_stamp)) {
    my_mesh_interfaces__msg__MeshTf__fini(msg);
    return false;
  }
  // tf_data
  if (!tf2_msgs__msg__TFMessage__init(&msg->tf_data)) {
    my_mesh_interfaces__msg__MeshTf__fini(msg);
    return false;
  }
  // map_in_flight
  return true;
}

void
my_mesh_interfaces__msg__MeshTf__fini(my_mesh_interfaces__msg__MeshTf * msg)
{
  if (!msg) {
    return;
  }
  // session_id
  // sequence_id
  // transmission_stamp
  builtin_interfaces__msg__Time__fini(&msg->transmission_stamp);
  // tf_data
  tf2_msgs__msg__TFMessage__fini(&msg->tf_data);
  // map_in_flight
}

bool
my_mesh_interfaces__msg__MeshTf__are_equal(const my_mesh_interfaces__msg__MeshTf * lhs, const my_mesh_interfaces__msg__MeshTf * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // session_id
  if (lhs->session_id != rhs->session_id) {
    return false;
  }
  // sequence_id
  if (lhs->sequence_id != rhs->sequence_id) {
    return false;
  }
  // transmission_stamp
  if (!builtin_interfaces__msg__Time__are_equal(
      &(lhs->transmission_stamp), &(rhs->transmission_stamp)))
  {
    return false;
  }
  // tf_data
  if (!tf2_msgs__msg__TFMessage__are_equal(
      &(lhs->tf_data), &(rhs->tf_data)))
  {
    return false;
  }
  // map_in_flight
  if (lhs->map_in_flight != rhs->map_in_flight) {
    return false;
  }
  return true;
}

bool
my_mesh_interfaces__msg__MeshTf__copy(
  const my_mesh_interfaces__msg__MeshTf * input,
  my_mesh_interfaces__msg__MeshTf * output)
{
  if (!input || !output) {
    return false;
  }
  // session_id
  output->session_id = input->session_id;
  // sequence_id
  output->sequence_id = input->sequence_id;
  // transmission_stamp
  if (!builtin_interfaces__msg__Time__copy(
      &(input->transmission_stamp), &(output->transmission_stamp)))
  {
    return false;
  }
  // tf_data
  if (!tf2_msgs__msg__TFMessage__copy(
      &(input->tf_data), &(output->tf_data)))
  {
    return false;
  }
  // map_in_flight
  output->map_in_flight = input->map_in_flight;
  return true;
}

my_mesh_interfaces__msg__MeshTf *
my_mesh_interfaces__msg__MeshTf__create(void)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  my_mesh_interfaces__msg__MeshTf * msg = (my_mesh_interfaces__msg__MeshTf *)allocator.allocate(sizeof(my_mesh_interfaces__msg__MeshTf), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(my_mesh_interfaces__msg__MeshTf));
  bool success = my_mesh_interfaces__msg__MeshTf__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
my_mesh_interfaces__msg__MeshTf__destroy(my_mesh_interfaces__msg__MeshTf * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    my_mesh_interfaces__msg__MeshTf__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
my_mesh_interfaces__msg__MeshTf__Sequence__init(my_mesh_interfaces__msg__MeshTf__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  my_mesh_interfaces__msg__MeshTf * data = NULL;

  if (size) {
    if (size > SIZE_MAX / sizeof(my_mesh_interfaces__msg__MeshTf)) {
      return false;
    }
    data = (my_mesh_interfaces__msg__MeshTf *)allocator.zero_allocate(size, sizeof(my_mesh_interfaces__msg__MeshTf), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = my_mesh_interfaces__msg__MeshTf__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        my_mesh_interfaces__msg__MeshTf__fini(&data[i - 1]);
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
my_mesh_interfaces__msg__MeshTf__Sequence__fini(my_mesh_interfaces__msg__MeshTf__Sequence * array)
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
      my_mesh_interfaces__msg__MeshTf__fini(&array->data[i]);
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

my_mesh_interfaces__msg__MeshTf__Sequence *
my_mesh_interfaces__msg__MeshTf__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  my_mesh_interfaces__msg__MeshTf__Sequence * array = (my_mesh_interfaces__msg__MeshTf__Sequence *)allocator.allocate(sizeof(my_mesh_interfaces__msg__MeshTf__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = my_mesh_interfaces__msg__MeshTf__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
my_mesh_interfaces__msg__MeshTf__Sequence__destroy(my_mesh_interfaces__msg__MeshTf__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    my_mesh_interfaces__msg__MeshTf__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
my_mesh_interfaces__msg__MeshTf__Sequence__are_equal(const my_mesh_interfaces__msg__MeshTf__Sequence * lhs, const my_mesh_interfaces__msg__MeshTf__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!my_mesh_interfaces__msg__MeshTf__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
my_mesh_interfaces__msg__MeshTf__Sequence__copy(
  const my_mesh_interfaces__msg__MeshTf__Sequence * input,
  my_mesh_interfaces__msg__MeshTf__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    if (input->size > SIZE_MAX / sizeof(my_mesh_interfaces__msg__MeshTf)) {
      return false;
    }
    const size_t allocation_size =
      input->size * sizeof(my_mesh_interfaces__msg__MeshTf);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    my_mesh_interfaces__msg__MeshTf * data =
      (my_mesh_interfaces__msg__MeshTf *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!my_mesh_interfaces__msg__MeshTf__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          my_mesh_interfaces__msg__MeshTf__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!my_mesh_interfaces__msg__MeshTf__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
