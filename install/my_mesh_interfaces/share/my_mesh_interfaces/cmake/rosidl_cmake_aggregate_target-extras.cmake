# generated from rosidl_cmake/cmake/rosidl_cmake_aggregate_target-extras.cmake.in

# Create a convenience aggregate target my_mesh_interfaces::my_mesh_interfaces
# that links all generated interface targets, so downstream packages can use
# a single modern CMake target name instead of ${my_mesh_interfaces_TARGETS}.
if(my_mesh_interfaces_TARGETS AND NOT TARGET my_mesh_interfaces::my_mesh_interfaces)
  add_library(my_mesh_interfaces::my_mesh_interfaces INTERFACE IMPORTED)
  set_target_properties(my_mesh_interfaces::my_mesh_interfaces PROPERTIES
    INTERFACE_LINK_LIBRARIES "${my_mesh_interfaces_TARGETS}")
endif()
