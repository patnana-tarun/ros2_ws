---
tags: [concept]
---
# Run logging

How the receiver's `tf_rolling_metrics` ([[Receiver (external)]]) splits a measurement session
into runs and writes the results. Added on [[2026-10-05]].

## Start / stop / exit
The node starts **idle**. Commands are typed on stdin, or published on `/mesh/logger_cmd`
([[Topics]]):

| Command | Effect |
|---|---|
| `start` | New run: Run ID + 1, fresh rolling window, one sample per second for `run_duration_sec` (60 s), then stops by itself |
| `stop`  | Ends the run early. Both CSVs are flushed and fsync'd |
| `exit`  | Stops any run and quits |

While idle, nothing is counted or logged. TF is still republished on `/tf_recovered`, and the
heartbeat history is still kept, so [[PDR measurement]] is correct from the first sample of
the next run. During the first `rolling_span_sec` of a run the window only reaches back to
the start of the run, so `span_sec` in the CSV is shorter than the configured span there.

The 60 s is timed on the monotonic clock, so a chrony step of the wall clock during a run
(the Pi has no RTC, [[Known limitations]] #21) neither ends nor stretches it. On `start`
the node checks `timedatectl`. If the clock is not synced, it warns that latency will be
empty. On `stop`, it warns if no map arrived during the whole run.

The Pi's `mesh_nodes` is built with `colcon build --symlink-install`, so edits to
`src/mesh_nodes/config/receiver.yaml` and to the node take effect on the next start without
rebuilding. Before that, the node read the copy in `install/`, which only changed on a build.
A terminal sourced before the switch to `--symlink-install` fails with
`PackageNotFoundError: No package metadata was found for mesh-nodes`: the metadata moved
to `build/mesh_nodes`, which only a fresh `source ~/ros2_ws/install/setup.bash` adds to
`PYTHONPATH`. Open a new terminal or source it again.

`ros2 launch` does not pass stdin through, so type commands only under `ros2 run`:

```bash
ros2 run mesh_nodes tf_rolling_metrics --ros-args \
  --params-file ~/ros2_ws/install/mesh_nodes/share/mesh_nodes/config/receiver.yaml \
  -p explorer_mac:=28:a4:4a:ac:3c:1c
# from any terminal, also works under ros2 launch:
ros2 topic pub --once /mesh/logger_cmd std_msgs/msg/String "{data: start}"
```

## IDs
- **Scenario ID**: one per program session. It is the largest `scenario_id` already in
  either CSV, plus 1, so it carries on across restarts.
- **Run ID**: 1, 2, 3 … within a scenario, one per `start`.

## Output files
Every run of every session is appended to the same two files. Both files have `timestamp`,
`scenario_id`, `run_id` and `map_active`.

| File | Contents |
|---|---|
| `~/mesh_results/mesh_runs.csv` | TF and map received/expected counts, combined PDR and loss, TF and map PDR, total/TF/map throughput over the window and over the last 1 s step, `th_req_kbytes_per_sec`, latency min/avg/max and jitter over both streams, TF and map average latency, hop count, TQ |
| `~/mesh_results/mesh_runs_normalized.csv` | `pdr_percent`, `latency_avg_ms`, `throughput_kbytes_per_sec`, `throughput_step_kbytes_per_sec`, `th_req_kbytes_per_sec`, and `pdr_n`, `latency_n`, `throughput_n`, `throughput_step_n` |

If an existing file has different columns (an older version of the node), it is renamed to
`<name>_old_<date>_<time>.csv`. A new file is started at the same path and the Scenario ID
carries on. Before, the node wrote to a new timestamped file instead, so every later session
was redirected again. Files from before the tf + map metrics: `mesh_tf_runs*.csv`.

**Both streams count** ([[Relay rates]]). PDR is in [[PDR measurement]]. Throughput is all
received bytes (TF at 56 bytes per transform, maps at 1 byte per cell) over the window. It is
a rolling average over `rolling_span_sec`, while `map_active` only looks at the last 1 s step.
The window always holds about span ÷ 3 maps, so throughput hardly changes with `map_active`:
on 2026-10-05, with a 20 s span and ~109 KB maps, it alternated between 36.3 KB/s (6 maps in the
window) and 41.6 KB/s (7 maps). With a span that is a multiple of 3 s (e.g. 6 s) the window
always holds the same number of maps, so map traffic shows up as a constant.

So the **step throughput** (`throughput_step_kbytes_per_sec`, plus TF and map parts) is also
written: bytes received in the last `rolling_step_sec` only. In seconds with a map it jumps;
in the laptop test with 6 s windows it was 35 KB/s with a map and 6 KB/s without, while the
window value stayed at 15.8 KB/s. `throughput_step_n` uses the same Th_req, which is a
per-window value.
Latency min/avg/max is over every TF and map packet. Jitter is the mean change in latency
between consecutive packets of the same stream, pooled over both streams. A 100 KB map next
to a 56-byte TF is not jitter.

**`map_active`** is 1 when a map was received in the last 1 s step. Maps arrive every 3 s, so
it is 1 in about a third of the samples (35 % in the test). The `stop` warning now fires
when no map arrived at all during a run.

Earlier versions took `map_active` from the sender's `map_in_flight` flag
([[Map-in-flight throttle]]), which got stuck at 1 when the hold wasn't shorter than the map
interval.

## Normalization
```
PDR_N        = PDR / 100
Latency_N    = max(1 − Latency / L_max, 0)      Latency = latency_avg_ms
Throughput_N = min(Throughput / Th_req, 1)      Throughput = TF + map KB/s
```
An empty input (PDR or latency not available) gives an empty normalized value.

| Limit | Value | Why |
|---|---|---|
| `Th_req` | **offered load, per window** (`th_req_kbps: 0`) | The throughput needed to carry everything the sender sent in the window: expected TF × mean TF size + expected maps × latest map size, over the window. It is written as `th_req_kbytes_per_sec`. A fixed value no longer works because the maps grow from ~11 KB to ~150 KB during exploration ([[Relay rates]]), so it would end up either always met or never met. `Throughput_N` = 1 means the link carried the whole load. Until 2026-10-05 it was fixed at 2.92 KB/s (the TF rate the throttle guaranteed) |
| `L_max`  | **1000 ms** | The receiver monitors the robot and is not in its control loop (the explorer's own Nav2/SLAM need TF within 0.1–0.2 s locally). About 1 s is the usual limit for a remote monitor before the shown pose stops matching the robot. Measured: clean windows at 15–50 ms → 0.95–0.98, degraded ones at 700–900 ms → 0.1–0.3 |

Both limits are parameters (`th_req_kbps`, `l_max_ms`) in `receiver.yaml`; `th_req_kbps > 0`
fixes Th_req. On the Pi the user has set `th_req_kbps: 3.00` and `l_max_ms: 2000`. With
maps now included, a fixed 3 KB/s is met almost always.
