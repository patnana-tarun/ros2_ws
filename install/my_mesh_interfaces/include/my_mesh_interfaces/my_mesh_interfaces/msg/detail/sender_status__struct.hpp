// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from my_mesh_interfaces:msg/SenderStatus.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/sender_status.hpp"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__STRUCT_HPP_
#define MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__my_mesh_interfaces__msg__SenderStatus __attribute__((deprecated))
#else
# define DEPRECATED__my_mesh_interfaces__msg__SenderStatus __declspec(deprecated)
#endif

namespace my_mesh_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct SenderStatus_
{
  using Type = SenderStatus_<ContainerAllocator>;

  explicit SenderStatus_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->session_id = 0ull;
      this->last_sequence_sent = 0ull;
    }
  }

  explicit SenderStatus_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->session_id = 0ull;
      this->last_sequence_sent = 0ull;
    }
  }

  // field types and members
  using _session_id_type =
    uint64_t;
  _session_id_type session_id;
  using _last_sequence_sent_type =
    uint64_t;
  _last_sequence_sent_type last_sequence_sent;

  // setters for named parameter idiom
  Type & set__session_id(
    const uint64_t & _arg)
  {
    this->session_id = _arg;
    return *this;
  }
  Type & set__last_sequence_sent(
    const uint64_t & _arg)
  {
    this->last_sequence_sent = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator> *;
  using ConstRawPtr =
    const my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__my_mesh_interfaces__msg__SenderStatus
    std::shared_ptr<my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__my_mesh_interfaces__msg__SenderStatus
    std::shared_ptr<my_mesh_interfaces::msg::SenderStatus_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const SenderStatus_ & other) const
  {
    if (this->session_id != other.session_id) {
      return false;
    }
    if (this->last_sequence_sent != other.last_sequence_sent) {
      return false;
    }
    return true;
  }
  bool operator!=(const SenderStatus_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct SenderStatus_

// alias to use template instance with default allocator
using SenderStatus =
  my_mesh_interfaces::msg::SenderStatus_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace my_mesh_interfaces

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__SENDER_STATUS__STRUCT_HPP_
