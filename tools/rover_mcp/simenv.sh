# Source this (bash) to get the environment the rover MCP server uses, so a sim you start by hand
# in a terminal is visible to it:   source ~/ros2_ws/tools/rover_mcp/simenv.sh
# - drops the VS Code snap's GTK/locale variables (docs/issues/GUI crashes in VS Code terminal.md)
# - isolates ROS and Gazebo traffic from the mesh: own domain, localhost only, no discovery server
# - NVIDIA PRIME offload for Gazebo/RViz rendering (as in data/demo_runs_2026-10-19/run_demo.sh)
unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE LOCPATH GIO_MODULE_DIR GSETTINGS_SCHEMA_DIR \
      GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR
[ -n "$XDG_DATA_DIRS_VSCODE_SNAP_ORIG" ] && export XDG_DATA_DIRS=$XDG_DATA_DIRS_VSCODE_SNAP_ORIG
[ -n "$XDG_CONFIG_DIRS_VSCODE_SNAP_ORIG" ] && export XDG_CONFIG_DIRS=$XDG_CONFIG_DIRS_VSCODE_SNAP_ORIG
export __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia \
       __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
unset ROS_DISCOVERY_SERVER FASTRTPS_DEFAULT_PROFILES_FILE ROS_LOCALHOST_ONLY
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_DOMAIN_ID=${ROVER_MCP_DOMAIN:-90}
export GZ_PARTITION=${ROVER_MCP_GZ_PARTITION:-rover_mcp}
export DISPLAY=${DISPLAY:-:1}
source /opt/ros/jazzy/setup.bash
source ${ROVER_MCP_WS:-$HOME/ros2_ws}/install/setup.bash
