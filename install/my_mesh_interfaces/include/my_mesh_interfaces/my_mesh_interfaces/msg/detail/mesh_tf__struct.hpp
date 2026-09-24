// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from my_mesh_interfaces:msg/MeshTf.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/mesh_tf.hpp"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__MESH_TF__STRUCT_HPP_
#define MY_MESH_INTERFACES__MSG__DETAIL__MESH_TF__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'transmission_stamp'
#include "builtin_interfaces/msg/detail/time__struct.hpp"
// Member 'tf_data'
#include "tf2_msgs/msg/detail/tf_message__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__my_mesh_interfaces__msg__MeshTf __attribute__((deprecated))
#else
# define DEPRECATED__my_mesh_interfaces__msg__MeshTf __declspec(deprecated)
#endif

namespace my_mesh_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct MeshTf_
{
  using Type = MeshTf_<ContainerAllocator>;

  explicit MeshTf_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : transmission_stamp(_init),
    tf_data(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->session_id = 0ull;
      this->sequence_id = 0ull;
      this->map_in_flight = false;
    }
  }

  explicit MeshTf_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : transmission_stamp(_alloc, _init),
    tf_data(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->session_id = 0ull;
      this->sequence_id = 0ull;
      this->map_in_flight = false;
    }
  }

  // field types and members
  using _session_id_type =
    uint64_t;
  _session_id_type session_id;
  using _sequence_id_type =
    uint64_t;
  _sequence_id_type sequence_id;
  using _transmission_stamp_type =
    builtin_interfaces::msg::Time_<ContainerAllocator>;
  _transmission_stamp_type transmission_stamp;
  using _tf_data_type =
    tf2_msgs::msg::TFMessage_<ContainerAllocator>;
  _tf_data_type tf_data;
  using _map_in_flight_type =
    bool;
  _map_in_flight_type map_in_flight;

  // setters for named parameter idiom
  Type & set__session_id(
    const uint64_t & _arg)
  {
    this->session_id = _arg;
    return *this;
  }
  Type & set__sequence_id(
    const uint64_t & _arg)
  {
    this->sequence_id = _arg;
    return *this;
  }
  Type & set__transmission_stamp(
    const builtin_interfaces::msg::Time_<ContainerAllocator> & _arg)
  {
    this->transmission_stamp = _arg;
    return *this;
  }
  Type & set__tf_data(
    const tf2_msgs::msg::TFMessage_<ContainerAllocator> & _arg)
  {
    this->tf_data = _arg;
    return *this;
  }
  Type & set__map_in_flight(
    const bool & _arg)
  {
    this->map_in_flight = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    my_mesh_interfaces::msg::MeshTf_<ContainerAllocator> *;
  using ConstRawPtr =
    const my_mesh_interfaces::msg::MeshTf_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<my_mesh_interfaces::msg::MeshTf_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<my_mesh_interfaces::msg::MeshTf_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      my_mesh_interfaces::msg::MeshTf_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<my_mesh_interfaces::msg::MeshTf_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      my_mesh_interfaces::msg::MeshTf_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<my_mesh_interfaces::msg::MeshTf_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<my_mesh_interfaces::msg::MeshTf_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<my_mesh_interfaces::msg::MeshTf_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__my_mesh_interfaces__msg__MeshTf
    std::shared_ptr<my_mesh_interfaces::msg::MeshTf_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__my_mesh_interfaces__msg__MeshTf
    std::shared_ptr<my_mesh_interfaces::msg::MeshTf_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const MeshTf_ & other) const
  {
    if (this->session_id != other.session_id) {
      return false;
    }
    if (this->sequence_id != other.sequence_id) {
      return false;
    }
    if (this->transmission_stamp != other.transmission_stamp) {
      return false;
    }
    if (this->tf_data != other.tf_data) {
      return false;
    }
    if (this->map_in_flight != other.map_in_flight) {
      return false;
    }
    return true;
  }
  bool operator!=(const MeshTf_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct MeshTf_

// alias to use template instance with default allocator
using MeshTf =
  my_mesh_interfaces::msg::MeshTf_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace my_mesh_interfaces

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__MESH_TF__STRUCT_HPP_
