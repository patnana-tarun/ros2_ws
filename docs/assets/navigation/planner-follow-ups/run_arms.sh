#!/bin/bash
# N-arm planner benchmark: all arms run side by side in each round, DUR s of sim time each.
# ARMS entries are tag|params_file|extra launch args.
B=${B:-$(dirname "$(readlink -f "$0")")}
WS=${WS:-$HOME/ros2_ws}; C=$WS/src/explorer_exploration/config
ROUNDS=${ROUNDS:-3}; DUR=${DUR:-600}
ARMS=(
  "navfn|$C/nav2_params.yaml|"
  "smac|$C/nav2_params_smac.yaml|"
  "smacpc|$C/nav2_params_smac.yaml|precheck_path:=true"
  "smacpcw|$C/nav2_params_smac_wide.yaml|precheck_path:=true"
)
unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE LOCPATH GIO_MODULE_DIR GSETTINGS_SCHEMA_DIR GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR
export XDG_DATA_DIRS=$XDG_DATA_DIRS_VSCODE_SNAP_ORIG XDG_CONFIG_DIRS=$XDG_CONFIG_DIRS_VSCODE_SNAP_ORIG
export __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
unset ROS_DISCOVERY_SERVER FASTRTPS_DEFAULT_PROFILES_FILE
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
source $WS/install/setup.bash

for i in $(seq 1 $ROUNDS); do
  echo "round $i: start $(date +%T)"; L=(); R=(); T=()
  for k in "${!ARMS[@]}"; do
    IFS='|' read -r tag cfg extra <<< "${ARMS[$k]}"; D=$((70 + 4*i + k)); T+=("${tag}_$i")
    ( export ROS_DOMAIN_ID=$D GZ_PARTITION=bench_$D
      exec setsid ros2 launch explorer_exploration bringup.launch.py gui:=false rviz:=false params_file:=$cfg $extra \
        > $B/${tag}_$i.launch.log 2>&1 ) &
    L+=($!)
  done
  sleep 5
  for k in "${!ARMS[@]}"; do
    D=$((70 + 4*i + k))
    ( export ROS_DOMAIN_ID=$D; exec python3 $B/bench_recorder.py $DUR $B/${T[$k]}.json > $B/${T[$k]}.rec.log 2>&1 ) &
    R+=($!)
  done
  wait "${R[@]}"
  echo "{" > $B/cpu_$i.json
  for k in "${!ARMS[@]}"; do
    pc=$(for p in $(pgrep -g ${L[$k]} -f planner_server); do awk '{printf "%.1f\n", ($14+$15)/100}' /proc/$p/stat; done | head -1)
    cc=$(for p in $(pgrep -g ${L[$k]} -f controller_server); do awk '{printf "%.1f\n", ($14+$15)/100}' /proc/$p/stat; done | head -1)
    sep=$([ $k -lt $((${#ARMS[@]}-1)) ] && echo , )
    echo "\"${T[$k]}\": {\"planner_cpu\": ${pc:-null}, \"controller_cpu\": ${cc:-null}}$sep" >> $B/cpu_$i.json
  done
  echo "}" >> $B/cpu_$i.json
  for g in "${L[@]}"; do kill -INT -- -$g 2>/dev/null; done; sleep 12
  for g in "${L[@]}"; do kill -9 -- -$g 2>/dev/null; done; sleep 3
  echo "round $i: done $(date +%T)"; grep -h done $B/*_$i.rec.log
done
echo ALL_DONE
