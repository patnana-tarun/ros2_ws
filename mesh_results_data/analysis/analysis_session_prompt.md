# Analysis session: link-quality score and relay-deployment rule

<!--
HOW TO USE (for the user, not part of the prompt). In a new claude.ai chat, attach these files,
then paste everything below the line.

Required, from ~/ros2_ws/mesh_results_data/csv/:
  1. mesh_runs_hops_rssi.csv               (427 KB, scenarios 1-8)
  2. mesh_runs_hops_rssi_scen31plus.csv    (819 KB, scenarios 31-42)
  Since 2026-10-25 these carry the finished score as 17 extra columns at the end (s_*, q_*,
  k_max_*, q_in_weights). For an independent analysis, attach copies with only the 41 measured
  columns (CRLF kept, gives back the original file byte for byte):
    cut -d, -f1-41 mesh_runs_hops_rssi.csv | sed 's/$/\r/' > /tmp/mesh_runs_hops_rssi.csv  (same for the other)

Recommended:
  3-4. the two notebook photos (scenario layouts)

Optional:
  5. mesh_runs_normalized_hops_rssi.csv and mesh_runs_normalized_hops_rssi_scen31plus.csv
     (only if you want the receiver's own pdr_n / latency_n / throughput_n columns)
  6. weights_critic_entropy_merec.py (the earlier objective-weighting method; removed from the folder,
     get it with: git show HEAD:mesh_results_data/weights_critic_entropy_merec.py > /tmp/weights_critic_entropy_merec.py)
  7. ~/snap/arduino/85/Arduino/sketch_aug29c/rssi_log.csv (677 KB, raw RSSI, to check alignment)
-->

---

## 1. Your role and the goal

You are analysing field measurements from a ROS 2 mesh-relay project. The data is in the attached
CSV files. Use your analysis (code) tool to load and analyse them in Python. Show tables and
charts in this chat.

I want three outcomes:

1. **Analysis.** A detailed analysis of the data collected in the scenarios described below,
   including the RSSI that was logged alongside it.
2. **Quality score.** A weighted equation that scores communication quality. Choose which
   parameters go into it, based on the data and on our project requirements, and give your own
   subjective weights with the reasoning behind each.
3. **Deployment decision.** We also want hard thresholds, on RSSI or on PDR, for deciding when to
   deploy a relay node and so extend the range of exploration. Recommend the best method for
   making that decision. It can be thresholds, the score, or a combination.

The **map stream matters more to us than TF**. Section 2 explains why, and your parameters,
weights and decision rule have to reflect it.

## 2. The system and our requirement

- **Explorer (L):** the laptop (Wi-Fi MAC `28:A4:4A:AC:3C:1C`). It stands in for the exploring
  robot, and runs the relay that sends the map and TF onto the mesh.
- **Base station (Pi):** a Raspberry Pi receiver. It measures everything in the CSVs. **Two
  different boards were used:**
  - radio `D8:3A:DD:13:54:64` on 2026-10-16 (scenarios 1–8);
  - radio `2C:CF:67:34:1D:9C` on 2026-10-22 (scenarios 31–41).

  Radio and antenna differences between the boards are a confound when you compare one hop with
  two hops.
- **Relay node (N1):** a Raspberry Pi Zero 2 W repeater (Wi-Fi MAC `2C:CF:67:23:DE:00`). This is
  the node we want to know when to deploy.
- **Network:** BATMAN-adv over an 802.11 IBSS cell (2.4 GHz channel 1). ROS 2 Jazzy with
  Fast DDS.

| Stream | QoS | Rate | Size |
|---|---|---|---|
| map | RELIABLE + TRANSIENT_LOCAL | one map every 3 s | ~109 KB typical (11–150 KB). About 36 KB/s, the bulk of all traffic |
| TF | BEST_EFFORT | ~33 msgs/s | 56 B per transform. About 2 KB/s |

**Why the map matters more.** The base station needs the map to see what has been explored and
to plan, and a lost map has no later sample to replace it. TF corrects itself: the next sample
replaces a dropped one.

**Our map requirement.** It's fine for the base station not to get every map as range grows,
within limits:
- **Target:** at most **one** map missed in a row, so a gap of about 6 s between maps.
- **Hard limit:** at most **two** maps missed in a row, so a gap of about 9 s. Three or more in
  a row is a failure.

Count a gap as `k = round(gap / 3 s) − 1` missed maps, and also report the raw gaps.

**Important consequence:** because the map is RELIABLE, link trouble shows up first as map
*latency* (retransmissions) and as maps arriving late or not at all. The combined PDR barely moves,
because TF makes up most of the packet count. A score built mainly on PDR hides exactly the effect
we care about.

TF has no requirement from us. If the score needs TF limits, propose values and justify them.

## 3. The scenarios

One unit on the axis is **58 cm**. Distances in metres are units × 0.58. Photos of the notebook
may be attached; this text includes the experimenter's corrections to them.

### Scenarios 1–8 (2026-10-16): direct link, laptop ↔ Pi

The link quality on a direct connection, in a straight-line environment. The Pi is fixed at
position 0 and the laptop moves. The ESP32 RSSI sniffer was at the laptop, listening to the Pi.

| Scenario | Laptop position (units) | Laptop–Pi distance |
|---|---|---|
| 1 | 0 | 0 m |
| 2 | 16 | 9.28 m (the notebook's "0.928 m" is a mistake) |
| 3 | 32 | 18.56 m |
| 4 | 48 | 27.84 m |
| 5 | 64 | 37.12 m |
| 6 | 80 | 46.40 m |
| 7 | 72 | 41.76 m |
| 8 | 76 | 44.08 m |

### Scenarios 31–34 (2026-10-22): range of the N1–Pi hop

The Pi is fixed. **The laptop and the ESP32 moved together with N1**, so the laptop was always
beside N1. The notebook says the laptop was fixed; that is wrong. The direct laptop–Pi link was
blocked on the laptop, so traffic went L → N1 → Pi. The RSSI is the ESP32 at N1 listening to the
Pi, i.e. the **N1 ↔ Pi** link.

| Scenario | N1 and laptop position (units) | N1–Pi distance |
|---|---|---|
| 31 | 38 | 22.04 m |
| 32 | 44 | 25.52 m |
| 33 | 50 | 29.00 m |
| 34 | 46 | 26.68 m |

### Scenarios 35–41 (2026-10-22): N1 fixed between laptop and Pi

The Pi is at 0 and **N1 is fixed at unit 48** (27.84 m from the Pi). The notebook drawing shows
46, but 48 is correct. The laptop moves away from N1. The direct link is blocked on the laptop, so
there are 2 hops. The ESP32 was at the laptop, listening to N1, so the RSSI is the **laptop ↔ N1**
link.

| Scenario | Laptop position (units) | Laptop–Pi distance | Laptop–N1 distance |
|---|---|---|---|
| 35 | 48 | 27.84 m | 0 m |
| 36 | 54 | 31.32 m | 3.48 m |
| 37 | 60 | 34.80 m | 6.96 m |
| 38 | 66 | 38.28 m | 10.44 m |
| 39 | 72 | 41.76 m | 13.92 m |
| 40 | 78 | 45.24 m | 17.40 m |
| 41 | 81 | 46.98 m | 19.14 m |

**Exclude scenario 42.** It is in `mesh_runs_hops_rssi_scen31plus.csv`, but it was not a real
test. Scenarios 9–30 are not in these files.

## 4. The data

### The attached files

All have one row per second.

| File | Contents |
|---|---|
| `mesh_runs_hops_rssi.csv` | scenarios 1–8, 1,146 rows. **Main file** |
| `mesh_runs_hops_rssi_scen31plus.csv` | scenarios 31–42, 2,189 rows (2,129 without 42). **Main file** |
| `mesh_runs_normalized_hops_rssi*.csv` (optional) | the receiver's normalized columns (`pdr_n`, `latency_n`, `throughput_n`, `throughput_step_n`) for the same rows; no per-stream columns |
| `weights_critic_entropy_merec.py` (optional) | the earlier objective weighting (section 5) |
| `rssi_log.csv` (optional) | the raw RSSI log the `rssi_*` columns were taken from |

### Columns in the main files

Every row starts with `timestamp, datetime, scenario_id, run_id, map_active, session_id,
span_sec, step_sec`, followed by these groups:

| Group | Columns |
|---|---|
| Counts | `tf_received, tf_expected, map_received, map_expected, packet_count, expected_count` |
| Delivery | `pdr_percent, loss_percent, tf_pdr_percent, map_pdr_percent` |
| Throughput over the window | `throughput_kbytes_per_sec` (+ `tf_…`, `map_…`) |
| Throughput over the last 1 s | `throughput_step_kbytes_per_sec` (+ `tf_…`, `map_…`) |
| Required throughput | `th_req_kbytes_per_sec` |
| Latency | `latency_min_ms, latency_avg_ms, latency_max_ms, jitter_ms, tf_latency_avg_ms, map_latency_avg_ms` |
| BATMAN | `hop_count`, `tq` (link quality 0–255) |
| RSSI | `rssi_mac, rssi_channel, rssi_samples, rssi_last_dbm, rssi_avg_dbm, rssi_weakest_dbm, rssi_strongest_dbm, rssi_filtered_dbm` |

### Measurement facts to respect

- **Runs and windows:** each run is 60 s, written once a second. Metrics come from a **6 s
  rolling window** (`span_sec`), so consecutive rows overlap and are not independent. Aggregate
  per run (`scenario_id`, `run_id`) or per scenario, and never compute anything across a run
  boundary.
- **Map gaps:** `map_active` = 1 means a map arrived in that 1 s step. Within each run, the time
  between consecutive `map_active` = 1 rows is the map gap, to 1 s resolution. This is the main
  measure for our requirement. The first and last gap of a run are cut off by the run's edges.
- **One combined PDR:** `pdr_percent` = (TF received + maps received) / (TF expected + maps
  expected). TF dominates it.
- **Coarse map PDR:** with about 2 maps per 6 s window, per-row `map_pdr_percent` takes only
  values like 0, 50, 66.7 and 100, and its median hides loss. Summed `map_received/map_expected`
  counts each map in several windows, so prefer the map gaps.
- **Fixed required throughput:** `th_req_kbytes_per_sec` is a fixed 60 KB/s here. Throughput is
  mostly map bytes, so it largely duplicates map delivery; check the correlation.
- **Latency:** the receiver's normalization is `latency_n = max(1 − latency_avg_ms / 2000, 0)`.
  `latency_avg_ms` pools TF and maps; use `map_latency_avg_ms` for the map. Latency relies on
  clock sync between the laptop and the Pi. Minimum latencies of about 38 ms suggest it held.
- **Empty cells are information, not missing data:**
  - Empty `pdr_percent`, `latency_avg_ms`, `hop_count` or `tq` means a total outage (no
    heartbeat or no route). Count it as 0 % delivery, never drop it.
  - Empty `map_latency_avg_ms` means no map arrived in that window.
  - Empty `rssi_*` occurs only in scenario 8, where the RSSI log stopped (31 of 67 rows).
- **RSSI:** an ESP32 on channel 1 reports RSSI only for frames from one target MAC.
  `rssi_filtered_dbm` is a median-of-3 plus EMA (α = 0.35) of `avg_dbm`, the value the sniffer
  recommends for decisions. RSSI was matched to the rows by the same second, so it may be up to
  1 s out of step. Its meaning changes per block:

  | Scenarios | ESP32 at | Target | Link measured |
  |---|---|---|---|
  | 1–8 | laptop | `D8:3A:DD:13:54:64` (Pi board A) | laptop ↔ Pi, the direct link in use |
  | 31–34 | N1, with the laptop beside it | `2C:CF:67:34:1D:9C` (Pi board B) | N1 ↔ Pi, the second hop |
  | 35–41 | laptop | `2C:CF:67:23:DE:00` (N1) | laptop ↔ N1, the first hop |

  Compare like with like. 31–34 tells you how far N1 can be from the base; 35–41 tells you how far
  the rover can be from N1. A deployment trigger on the rover has to use the rover-side link, as
  in 1–8 and 35–41.

### Orientation snapshot

I computed this as a quick sanity check. Recompute it yourself.

| Sc | Median TQ | Median PDR % | Maps rx/exp (summed) | Max map gap (s) | Median map latency (ms) | Median RSSI (dBm) |
|---|---|---|---|---|---|---|
| 1 | 242 | 100 | 115/115 | 3 | 206 | −51.1 |
| 2 | 254 | 100 | 349/349 | 4 | 236 | −47.0 |
| 3 | 237 | 100 | 345/345 | 3 | 365 | −58.8 |
| 4 | 241 | 100 | 349/349 | 3 | 349 | −59.3 |
| 5 | 227 | 99.5 | 250/341 | 34 | 702 | −71.7 |
| 6 | 235 | 100 | 229/233 | 4 | 646 | −71.0 |
| 7 | 238 | 100 | 345/351 | 4 | 773 | −78.5 |
| 8 | 194 | 75 | 6/48 | (almost no maps) | 3,631 | −73.0 (partial) |
| 31 | 223 | 99.0 | 250/344 | 21 | 175 | −65.1 |
| 32 | 221 | 98.6 | 258/346 | 12 | 158 | −67.2 |
| 33 | 207 | 91.4 | 102/465 | 18 | 207 | −76.0 |
| 34 | 231 | 98.0 | 246/352 | 24 | 180 | −74.2 |
| 35 | 226 | 95.5 | 159/354 | 12 | 262 | −63.3 |
| 36 | 209 | 98.0 | 199/343 | 15 | 202 | −74.2 |
| 37 | 221 | 98.0 | 216/355 | 15 | 251 | −77.2 |
| 38 | 219 | 99.0 | 290/349 | 9 | 301 | −81.8 |
| 39 | 207 | 99.5 | 304/335 | 9 | 302 | −81.6 |
| 40 | 227 | 100 | 334/346 | 8 | 390 | −81.2 |
| 41 | 142 | 98.3 | 314/517 | 11 | 1,245 | −89.5 |

Things worth explaining:
- **Scenario 8 failed at 44 m, but scenario 6 worked at 46 m,** and scenario 5 had one long
  outage. Distance alone doesn't predict failure.
- **Combined PDR stays at 91–100 %** while map gaps reach 10–34 s.
- **Scenarios 35–37 (laptop close to N1) had longer map gaps than 38–40 (laptop further away).**
  Check run by run whether this is real.
- **TQ stays above 200** in several scenarios that break the map requirement.

## 5. Earlier work: reuse the method, not the result

An earlier script (`weights_critic_entropy_merec.py`, if attached) weighted only throughput,
latency and PDR objectively (CRITIC, Entropy, MEREC) on older data. It gave Throughput 0.63,
Latency 0.28 and PDR 0.09.

Objective methods reward variance, not importance. PDR got almost no weight because it barely
varied, not because it matters little. Use them as a cross-check against your subjective weights,
not as the answer.

## 6. What we already know about deployment

From our own earlier tests and notes:
- **The rover can't trigger on PDR or latency:** they are computed at the base station and reach
  the rover too late. A trigger at the rover should use what the rover measures itself: RSSI,
  BATMAN TQ, and Wi-Fi retries.
- **Delivery falls off a cliff while RSSI falls smoothly,** so trigger on an RSSI margin above
  the cliff, smoothed over 5–10 s.
- **TQ lags about 60 s** (it is built from one routing packet per second), so it is a poor fast
  trigger.
- **The drop point decides the relay's own link quality.** A relay dropped at the edge of range
  starts on a dying link. In an earlier walk test, dropping node1 just before the drop-out point
  failed: N1 was itself almost out of range of the Pi.
- **In open ground, the route can flip** between direct and via N1 when the two are of similar
  quality.

## 7. Deliverables

1. **Data audit.** Check rows per scenario and run, outages, empty cells, and RSSI coverage.
   Confirm each block matches section 3 (hop count, RSSI target, timing).
2. **Analysis per scenario and per run:**
   - The map, first:
     - map gaps: the distribution (median, p95, max) and the share of time with 0, 1, 2 and 3+
       maps missed in a row;
     - map latency (median and p90);
     - map throughput against the offered load.
   - TF, second: PDR, latency and jitter.
   - Each metric plotted against RSSI, TQ and distance.
   - Find the cliff: the RSSI where the map requirement starts to break.
   - Compare one hop (1–8) with two hops (31–41) at similar RSSI, minding the board confound.
   - Compare 31–34 (N1–Pi hop varied) with 35–41 (first hop varied) to see which hop limits the
     two-hop route.
3. **Parameter selection for the score.** Start from these candidates: map gap or missed-map
   count, map latency, map throughput, TF PDR, TF latency, jitter, RSSI and TQ.
   - Drop the redundant ones (show the correlations) and the uninformative ones.
   - Say which parameters the rover can measure itself in real time and which only the base
     station knows.
4. **The weighted equation.**
   - Normalization for each parameter. Anchor the map one on our requirement: full marks with no
     maps missed, still acceptable with one missed, and zero with three or more in a row. Justify
     the value you give to two missed.
   - Your subjective weights, justified by the map-first priority.
   - A comparison with objective weights (CRITIC, Entropy, MEREC, optionally AHP).
   - A sensitivity analysis: does the scenario ranking survive ±20 % changes to the weights?
   - Score every scenario, and check the ranking is physically plausible.
5. **The deployment rule.**
   - Evaluate hard thresholds on RSSI and on PDR, and the score.
   - Recommend one method. Include smoothing, hysteresis or a margin so it doesn't flap, and say
     where to drop the node relative to the threshold.
   - Success criterion: the node is deployed before the link reaches two maps missed in a row,
     and preferably while it misses at most one.
   - Replay the rule on the recorded rows: where would it have triggered, and would that have
     been early enough?
   - If a two-signal rule is better, explain it. For example, an RSSI trigger at the rover with a
     map-gap confirmation from the base.
6. **Limitations, and the next measurements** that would make the thresholds trustworthy.

## 8. Output

- **In this chat:** the report, with tables and charts. Give the code you used, so it can be
  rerun on new data.
- **At the end:** a short **"Notes for the project docs"** section in plain Markdown. Include:
  - the chosen parameters and weights;
  - the equation;
  - the thresholds and the deployment rule;
  - the key numbers;
  - the open limitations.

  I will paste it into our documentation, which feeds the project report, so keep it
  report-quality.
- **Labelling:** say which conclusions rest on few runs (most scenarios have 2–5 runs of 60 s).
  Separate measured facts from interpretation.
