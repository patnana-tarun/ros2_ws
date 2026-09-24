// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from my_mesh_interfaces:msg/MeshMap.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "my_mesh_interfaces/msg/mesh_map.hpp"


#ifndef MY_MESH_INTERFACES__MSG__DETAIL__MESH_MAP__STRUCT_HPP_
#define MY_MESH_INTERFACES__MSG__DETAIL__MESH_MAP__STRUCT_HPP_

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
// Member 'map_data'
#include "nav_msgs/msg/detail/occupancy_grid__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__my_mesh_interfaces__msg__MeshMap __attribute__((deprecated))
#else
# define DEPRECATED__my_mesh_interfaces__msg__MeshMap __declspec(deprecated)
#endif

namespace my_mesh_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct MeshMap_
{
  using Type = MeshMap_<ContainerAllocator>;

  explicit MeshMap_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : transmission_stamp(_init),
    map_data(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->session_id = 0ull;
      this->sequence_id = 0ull;
    }
  }

  explicit MeshMap_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : transmission_stamp(_alloc, _init),
    map_data(_alloc, _init)
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
  using _transmission_stamp_type =
    builtin_interfaces::msg::Time_<ContainerAllocator>;
  _transmission_stamp_type transmission_stamp;
  using _map_data_type =
    nav_msgs::msg::OccupancyGrid_<ContainerAllocator>;
  _map_data_type map_data;

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
  Type & set__map_data(
    const nav_msgs::msg::OccupancyGrid_<ContainerAllocator> & _arg)
  {
    this->map_data = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    my_mesh_interfaces::msg::MeshMap_<ContainerAllocator> *;
  using ConstRawPtr =
    const my_mesh_interfaces::msg::MeshMap_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<my_mesh_interfaces::msg::MeshMap_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<my_mesh_interfaces::msg::MeshMap_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      my_mesh_interfaces::msg::MeshMap_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<my_mesh_interfaces::msg::MeshMap_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      my_mesh_interfaces::msg::MeshMap_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<my_mesh_interfaces::msg::MeshMap_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<my_mesh_interfaces::msg::MeshMap_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<my_mesh_interfaces::msg::MeshMap_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__my_mesh_interfaces__msg__MeshMap
    std::shared_ptr<my_mesh_interfaces::msg::MeshMap_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__my_mesh_interfaces__msg__MeshMap
    std::shared_ptr<my_mesh_interfaces::msg::MeshMap_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const MeshMap_ & other) const
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
    if (this->map_data != other.map_data) {
      return false;
    }
    return true;
  }
  bool operator!=(const MeshMap_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct MeshMap_

// alias to use template instance with default allocator
using MeshMap =
  my_mesh_interfaces::msg::MeshMap_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace my_mesh_interfaces

#endif  // MY_MESH_INTERFACES__MSG__DETAIL__MESH_MAP__STRUCT_HPP_
