# mesh_results_data

Laptop copy of the mesh-relay field-test data (one row per second, written by the receiver Pi in
`~/ros2_ws/mesh_results/`), plus the weighting scripts, analysis pages and presentation pages
built from it. Column meanings: `docs/concepts/Run logging.md`.

## csv/: the measurements
| File | Rows | Scenarios | Recorded | What it is |
|---|---|---|---|---|
| `mesh_runs.csv` | 1600 | 1–10 | 2026-10-09 | early runs: PDR, latency, throughput, hops, TQ |
| `mesh_runs_normalized.csv` | 1600 | 1–10 | 2026-10-09 | the same rows as 0–1 values (`pdr_n`, `latency_n`, `throughput_n`) + `score_*` columns |
| `mesh_runs_hops_rssi.csv` | 1146 | 1–8 | 2026-10-16 | field tests case 1 (direct link) with per-stream map/TF columns and RSSI. **Main file** |
| `mesh_runs_normalized_hops_rssi.csv` | 1146 | 1–8 | 2026-10-16 | the receiver's normalized columns for the same rows |
| `mesh_runs_hops_rssi_scen31plus.csv` | 2189 | 31–42 | 2026-10-22 | field tests cases 2–3 (relay node). 42 was not a test. **Main file** |
| `mesh_runs_normalized_hops_rssi_scen31plus.csv` | 2189 | 31–42 | 2026-10-22 | the receiver's normalized columns for the same rows |

Read by `reports/review_3/scripts/comm_analysis.py` (the two main files) and, through it, by
`presentation/src/make_pages.py`.

The four field-test files end with 17 **score columns** (added 2026-10-25; the measured columns
before them are unchanged). The script that wrote them was removed later that day, so they are
fixed values now; a copy is in `~/Downloads/mesh_results_data_field_tests_2026-10-25.tar.gz`.
Run values repeat on every row of the run, scenario values on every row of the scenario:

| Column | Level | Meaning |
|---|---|---|
| `s_gap` | run | map-gap criterion: time-weighted value of k maps missed in a row (k 0/1/2/3+ → 1.0/0.7/0.3/0) |
| `s_lat` | run | median map latency: 1 at ≤ 300 ms, 0 at ≥ 3000 ms |
| `s_tfpdr` | run | mean TF PDR (empty = 0 %): 1 at ≥ 99 %, 0 at ≤ 85 % |
| `s_tflat` | run | median TF latency: 1 at ≤ 100 ms, 0 at ≥ 1000 ms |
| `q_subjective` | run | Q = Σ w·S with the project's weights 0.50/0.25/0.15/0.10 (the one used) |
| `q_ahp`, `q_critic`, `q_entropy`, `q_merec` | run | Q with the AHP, CRITIC, Entropy and MEREC weights (cross-checks) |
| `k_max_run` | run | most maps missed in a row in the run (≤ 1 target met, 2 hard limit only, ≥ 3 failed) |
| `q_in_weights` | run | 1 = the run fed the objective weights (scenario not 6, 7, 8, 42 and ≥ 30 rows) |
| `q_scenario` | scenario | subjective Q pooled over all runs of the scenario (gap shares over all gaps, medians over all rows), as in the report; not the mean of the run Qs |
| `q_scenario_ahp` … `_merec` | scenario | the same with the other weight sets |
| `k_max_scenario` | scenario | most maps missed in a row in any run of the scenario |

A run with no value at all for a latency or TF PDR scores 0 on that criterion (only 8/2, 8 rows).

## weights/: criteria weights for the quality score
- `weights_calculator_kit/`: **the current method**, the calculator (subjective, AHP, CRITIC,
  Entropy, MEREC + sensitivity check) for the field-test criteria; how it works: `WEIGHTS_GUIDE.md`.
  The kit's weights on the two main files (`--exclude 6 7 8 42`, 49 runs) match its guide §6
  and the report. The score columns count a gap cut by a run's start or end in full (+1 s), like
  `reports/review_3/scripts/comm_analysis.py`, so they reproduce the report's Q; the kit ignores
  such gaps under 4 s, which is how the weights were made.
- The first method (CRITIC, Entropy, MEREC on throughput, latency and PDR, 2026-10-09; its
  `score_*` columns are in `csv/mesh_runs_normalized.csv`) was removed on 2026-10-25; its script
  and outputs are in git history (`git show HEAD:mesh_results_data/weights_critic_entropy_merec.py`).

## analysis/
- `mesh_run_analysis.html`: interactive explorer. It opens with the two scored main field-test
  files embedded (as of 2026-10-25); the first CSV you load from `csv/` replaces them. The scores
  tab shows Q (pooled per scenario, five weight sets, largest k, run-to-run spread, Kendall τ
  between weight sets) for scored files, and the old `score_*` view for `mesh_runs_normalized.csv`.
- `analysis_session_prompt.md`: prompt for a claude.ai session that analyses the field tests.

## presentation/
- `field_tests_case1.html` (direct link), `field_tests_case2_3.html` (relay node): slide-sized
  interactive pages, built by `src/make_pages.py` from `src/template.html` (plotly is inlined,
  so they work offline). A menu in the quality-score chart picks the weight set shown there and in
  the "Score Q" box: subjective (the one used, default) or AHP, CRITIC, Entropy, MEREC, read from
  `src/weights.csv` (the kit's output) and applied to the report's S terms. Rebuild after the
  weights change.
- `Mesh Relay Field Tests Layouts, Analysis and Deployment Rule.pdf`: the field-test write-up.
