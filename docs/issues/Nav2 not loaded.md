---
tags: [issue]
---
# Nav2 not loaded

**Symptom.** The robot sits still. Gazebo, SLAM, RViz and TAD all run, the map grows and TAD
publishes `/best_goal`, but the coordinator never logs `Sending goal`. It stays at
`waiting for Nav2...` and uses ~45 % CPU.

**Diagnosis (2026-09-30).**
- `ros2 action info /navigate_to_pose` showed 5 clients and **0 servers**.
- `/cmd_vel` had no publisher.
- `/nav2_container` was running but `list_nodes` returned an empty list, and `launch.log` had
  no `Loaded node` lines.

**Cause.** Nav2 ran in a component container (`use_composition` defaults to True). The launch
process loads each Nav2 node by calling the container's `load_node` service. In Fast DDS
discovery-server mode ([[Discovery server not running]]) that call missed the container during
startup and gave up silently, so the container stayed empty. The same stack loaded Nav2 fine
without the discovery server.

**Fix.** `bringup.launch.py` now passes `use_composition: False`. Each Nav2 server runs as its own
process, with no service call at startup.

**Verified 2026-09-30,** headless, without the discovery server: `/bt_navigator` served
`/navigate_to_pose`, `/cmd_vel` ran at 20 Hz, and the first goal was reached in 25 s. Not yet
verified in discovery-server mode.

## Second form: lifecycle bringup hangs (2026-10-06)

**Symptom.** Same as above, but every Nav2 node is running. `lifecycle_manager_navigation`
stops at `Configuring controller_server`, `lifecycle_manager_slam` at `Configuring map_saver`,
and `bt_navigator` is never configured. `controller_server` logs `failed to send response to
/controller_server/change_state (timeout): client will not receive response`.

**Cause.** Seen first in discovery-server mode, but **not limited to it**. On 2026-10-09 the
same hang happened twice in 3 GUI launches with plain local discovery (no server): once at
`Configuring controller_server` (no Nav2, robot never moved), once at `Configuring map_saver`
(SLAM never activated, no map). When ~25 processes start at once, the server is slow to
match endpoints. A node finishes configuring, but its reply writer hasn't yet matched the
lifecycle manager's reader, so the reply is dropped. The lifecycle manager never retries, so it
waits forever. It is intermittent: once startup was over, service calls through the same server
were answered 3/3.

**Earlier workaround.** Ctrl+C and relaunch. Running simulation without the server
(`unset ROS_DISCOVERY_SERVER FASTRTPS_DEFAULT_PROFILES_FILE`) avoids the first form. A retrying
lifecycle supervisor plus a CLIENT discovery profile was tried on 2026-10-06 and reverted at
the user's request ([[2026-10-06]]).

**Fix (2026-10-15): delayed startup.** The race comes from a client that calls as soon as it
sees the server, before the server side has matched the client's endpoints. The rule is that
every client is created well before its first call:
- Both lifecycle managers run with `autostart: False`. They still create their `change_state`
  clients at launch, but send nothing yet.
- The `lifecycle_startup` node ([[explorer_exploration]]) also starts at launch and creates its
  `manage_nodes` clients. After `startup_delay` s (default 8, wall time) it sends STARTUP once to
  `lifecycle_manager_slam` and `lifecycle_manager_navigation`, logs `nodes active` for each
  reply, and exits. Nothing retries.
- A first version sent STARTUP with `ros2 service call` from a `TimerAction`. It hung 1 of 8
  times: the CLI is a new process that sends straight away, so SLAM's STARTUP request was lost
  (both CLI calls timed out without a reply). That is the same race again.

**Verified 2026-10-15,** GUI launches (Gazebo + RViz) with the discovery server running
(Recv-Q 0 before each run):

| Launch | Runs | Hung | SLAM active | Nav2 active | First goal |
|--------|------|------|-------------|-------------|------------|
| old (autostart) | 8 | 1 (`Configuring slam_toolbox`, reply dropped) | 3–4 s | 6–8 s | 6–7 s |
| `ros2 service call` after 8 s | 8 | 1 (SLAM STARTUP lost) | 11–12 s | 14–15 s | 14–15 s |
| `lifecycle_startup` node | 12 | 0 | 10 s | 12–14 s | 12 s |

The cost is ~6 s longer startup. Not yet verified: on the real robot (`sim:=false`), and
without the discovery server.
