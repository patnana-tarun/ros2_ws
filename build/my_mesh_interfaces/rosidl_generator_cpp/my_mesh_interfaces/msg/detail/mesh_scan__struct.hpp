// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from my_mesh_interfaces:msg/MeshScan.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/mesh_scan.hpp"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__STRUCT_HPP_
#define MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'map_data'
#include "nav_msgs/msg/detail/occupancy_grid__struct.hpp"
// Member 'transmission_stamp'
#include "builtin_interfaces/msg/detail/time__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__my_mesh_interfaces__msg__MeshScan __attribute__((deprecated))
#else
# define DEPRECATED__my_mesh_interfaces__msg__MeshScan __declspec(deprecated)
#endif

namespace my_mesh_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct MeshScan_
{
  using Type = MeshScan_<ContainerAllocator>;

  explicit MeshScan_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : map_data(_init),
    transmission_stamp(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->session_id = 0ull;
      this->sequence_id = 0ull;
    }
  }

  explicit MeshScan_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : map_data(_alloc, _init),
    transmission_stamp(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->session_id = 0ull;
      this->sequence_id = 0ull;
    }
  }

  // field types and members
  using _session_id_type =
    uint64_t;
  _session_id_type session_id;
  using _sequence_id_type =
    uint64_t;
  _sequence_id_type sequence_id;
  using _map_data_type =
    nav_msgs::msg::OccupancyGrid_<ContainerAllocator>;
  _map_data_type map_data;
  using _transmission_stamp_type =
    builtin_interfaces::msg::Time_<ContainerAllocator>;
  _transmission_stamp_type transmission_stamp;

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
  Type & set__map_data(
    const nav_msgs::msg::OccupancyGrid_<ContainerAllocator> & _arg)
  {
    this->map_data = _arg;
    return *this;
  }
  Type & set__transmission_stamp(
    const builtin_interfaces::msg::Time_<ContainerAllocator> & _arg)
  {
    this->transmission_stamp = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    my_mesh_interfaces::msg::MeshScan_<ContainerAllocator> *;
  using ConstRawPtr =
    const my_mesh_interfaces::msg::MeshScan_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<my_mesh_interfaces::msg::MeshScan_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<my_mesh_interfaces::msg::MeshScan_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      my_mesh_interfaces::msg::MeshScan_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<my_mesh_interfaces::msg::MeshScan_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      my_mesh_interfaces::msg::MeshScan_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<my_mesh_interfaces::msg::MeshScan_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<my_mesh_interfaces::msg::MeshScan_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<my_mesh_interfaces::msg::MeshScan_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__my_mesh_interfaces__msg__MeshScan
    std::shared_ptr<my_mesh_interfaces::msg::MeshScan_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__my_mesh_interfaces__msg__MeshScan
    std::shared_ptr<my_mesh_interfaces::msg::MeshScan_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const MeshScan_ & other) const
  {
    if (this->session_id != other.session_id) {
      return false;
    }
    if (this->sequence_id != other.sequence_id) {
      return false;
    }
    if (this->map_data != other.map_data) {
      return false;
    }
    if (this->transmission_stamp != other.transmission_stamp) {
      return false;
    }
    return true;
  }
  bool operator!=(const MeshScan_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct MeshScan_

// alias to use template instance with default allocator
using MeshScan =
  my_mesh_interfaces::msg::MeshScan_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace my_mesh_interfaces

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__MESH_SCAN__STRUCT_HPP_
