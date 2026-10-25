#!/bin/bash
# A/B: NavFn (A) vs Smac Lattice (B), PAIRS pairs, run side by side, DUR s of sim time each.
B=${B:-$(dirname "$(readlink -f "$0")")}   # results go next to this script unless B is set
WS=${WS:-$HOME/ros2_ws}
PAIRS=${PAIRS:-3}; DUR=${DUR:-600}
CFG_A=$WS/src/explorer_exploration/config/nav2_params.yaml
CFG_B=$WS/src/explorer_exploration/config/nav2_params_smac.yaml

unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE LOCPATH GIO_MODULE_DIR GSETTINGS_SCHEMA_DIR GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR
export XDG_DATA_DIRS=$XDG_DATA_DIRS_VSCODE_SNAP_ORIG XDG_CONFIG_DIRS=$XDG_CONFIG_DIRS_VSCODE_SNAP_ORIG
export __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
# isolated, local-only discovery for the benchmark sims (the mesh discovery server is not involved)
unset ROS_DISCOVERY_SERVER FASTRTPS_DEFAULT_PROFILES_FILE
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
source $WS/install/setup.bash

start() {  # $1 tag  $2 domain  $3 cfg
  ( export ROS_DOMAIN_ID=$2 GZ_PARTITION=bench_$2
    exec setsid ros2 launch explorer_exploration bringup.launch.py gui:=false rviz:=false params_file:=$3 \
      > $B/$1.launch.log 2>&1 ) &
  LPID=$!
}
rec() {  # $1 tag $2 domain
  ( export ROS_DOMAIN_ID=$2; exec python3 $B/bench_recorder.py $DUR $B/$1.json > $B/$1.rec.log 2>&1 ) &
  RPID=$!
}
cpu_of() {  # $1 domain-tagged launch pgid, $2 exe name -> cpu seconds
  for p in $(pgrep -g $1 -f "$2"); do awk '{printf "%.1f\n", ($14+$15)/100}' /proc/$p/stat; done | head -1
}

for i in $(seq 1 $PAIRS); do
  DA=$((60 + 2*i)); DB=$((61 + 2*i))
  echo "pair $i: start $(date +%T)"
  start navfn_$i $DA $CFG_A; PA=$LPID; start smac_$i $DB $CFG_B; PB=$LPID
  sleep 5
  rec navfn_$i $DA; RA=$RPID; rec smac_$i $DB; RB=$RPID
  wait $RA $RB
  GA=$PA; GB=$PB
  echo "{\"navfn_$i\": {\"planner_cpu\": $(cpu_of $GA planner_server || echo null), \"controller_cpu\": $(cpu_of $GA controller_server || echo null)}, \"smac_$i\": {\"planner_cpu\": $(cpu_of $GB planner_server || echo null), \"controller_cpu\": $(cpu_of $GB controller_server || echo null)}}" > $B/cpu_$i.json
  kill -INT -- -$GA -$GB 2>/dev/null; sleep 12; kill -9 -- -$GA -$GB 2>/dev/null; sleep 3
  echo "pair $i: done $(date +%T)"; cat $B/navfn_$i.rec.log $B/smac_$i.rec.log | grep done
done
echo ALL_DONE
