cmake_minimum_required(VERSION 3.8)
project(explorer_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY urdf launch rviz config
  DESTINATION share/${PROJECT_NAME}
)

# Procedural cave world: meshes and textures are generated at build time (several MB,
# so they are not committed). See scripts/generate_cave.py.
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(CAVE_OUT ${CMAKE_CURRENT_BINARY_DIR}/cave)
add_custom_command(
  OUTPUT ${CAVE_OUT}/worlds/cave.sdf
  COMMAND ${CMAKE_COMMAND} -E rm -rf ${CAVE_OUT}
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_cave.py --out ${CAVE_OUT}
  DEPENDS scripts/generate_cave.py
  COMMENT "Generating cave world"
)
add_custom_target(cave_world ALL DEPENDS ${CAVE_OUT}/worlds/cave.sdf)
install(DIRECTORY ${CAVE_OUT}/models ${CAVE_OUT}/worlds DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/generate_cave.py DESTINATION lib/${PROJECT_NAME})

ament_package()
