#!/bin/bash
# Tunnel-tracking runs WITH the GUI (Gazebo + RViz), one at a time, DUR s of sim time each.
# RUNS entries: tag|params file|launch args. Run order is interleaved so the arms see the same machine.
S=$(dirname "$(readlink -f "$0")")   # this script and the recorder
B=${B:-$S}                            # output folder
WS=${WS:-$HOME/ros2_ws}; C=$WS/install/explorer_exploration/share/explorer_exploration/config
DUR=${DUR:-600}
RUNS=${RUNS:-"base_1|$C/nav2_params.yaml| smooth_1|$C/nav2_params.yaml|bt_xml:=explore_nav_to_pose_smooth.xml tuned_1|$C/nav2_params_tunnel.yaml|bt_xml:=explore_nav_to_pose_smooth.xml base_2|$C/nav2_params.yaml| smooth_2|$C/nav2_params.yaml|bt_xml:=explore_nav_to_pose_smooth.xml tuned_2|$C/nav2_params_tunnel.yaml|bt_xml:=explore_nav_to_pose_smooth.xml"}

unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE LOCPATH GIO_MODULE_DIR GSETTINGS_SCHEMA_DIR GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR
export XDG_DATA_DIRS=$XDG_DATA_DIRS_VSCODE_SNAP_ORIG XDG_CONFIG_DIRS=$XDG_CONFIG_DIRS_VSCODE_SNAP_ORIG
export __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
unset ROS_DISCOVERY_SERVER FASTRTPS_DEFAULT_PROFILES_FILE
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-90} GZ_PARTITION=tunnel_gui
source $WS/install/setup.bash

for run in $RUNS; do
  IFS='|' read -r tag cfg extra <<< "$run"
  echo "$tag: start $(date +%T)  params=$(basename $cfg) $extra"
  ( exec setsid ros2 launch explorer_exploration bringup.launch.py gui:=true rviz:=true params_file:=$cfg $extra \
      > $B/$tag.launch.log 2>&1 ) &
  L=$!
  sleep 5
  python3 $S/tunnel_recorder.py $DUR $B/$tag > $B/$tag.rec.log 2>&1
  kill -INT -- -$L 2>/dev/null; sleep 12; kill -9 -- -$L 2>/dev/null; sleep 4
  echo "$tag: done $(date +%T)"; grep -h done $B/$tag.rec.log
done
echo ALL_DONE
