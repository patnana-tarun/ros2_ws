# How the weights of the quality score are calculated

A guide to `weights_calculator.py`. It explains each method in plain terms, then shows how to run the program on any dataset that has the needed columns.

---

## 1. The idea in one paragraph

The quality score is a weighted sum:

```
Q = w1·S_gap + w2·S_lat + w3·S_tfpdr + w4·S_tflat        (w1 + w2 + w3 + w4 = 1)
```

Each **S** is a criterion scaled to 0–1, where 1 is best. Each **w** is a weight that says how much that criterion counts. The program does three jobs:

1. **Turns raw logs into criteria.** One-second rows become one 0–1 value per criterion for each run.
2. **Calculates weights five ways.** One way is your own choice (subjective), one is structured judgement (AHP), and three are computed from the data (CRITIC, Entropy, MEREC).
3. **Checks the result.** It scores every scenario with each weight set, then tests whether the ranking survives ±20 % changes to the weights.

**Key point:** the objective methods (CRITIC, Entropy, MEREC) measure **how much a criterion varies**, not **how important it is**. A criterion that never changes gets almost no weight, even if it matters a lot. That is why our final weights are subjective and the objective ones serve only as a cross-check.

---

## 2. Step 1: from raw rows to criteria

The program groups rows by `(scenario_id, run_id)` and never mixes two runs.

| Criterion | Raw input | How it becomes 0–1 |
|---|---|---|
| **S_gap** (map gap) | `map_active`, `timestamp` | Time between maps → k maps missed in a row → value of k, weighted by time (below) |
| **S_lat** (map latency) | `map_latency_avg_ms` (median) | 1 at ≤ 300 ms, 0 at ≥ 3,000 ms, straight line between |
| **S_tfpdr** (TF PDR) | `tf_pdr_percent` (mean, empty = 0 %) | 1 at ≥ 99 %, 0 at ≤ 85 % |
| **S_tflat** (TF latency) | `tf_latency_avg_ms` (median) | 1 at ≤ 100 ms, 0 at ≥ 1,000 ms |

### How S_gap is worked out

1. **Find the gaps.** Gaps are the times between rows where `map_active = 1`. A short gap at the start or end of a run (< 4 s) is ignored, because the run just began or ended between two maps.
2. **Count missed maps** in each gap: `k = round(gap / 3 s) − 1`. For example, a 3 s gap gives k = 0, a 6 s gap k = 1, and a 9 s gap k = 2.
3. **Give each k a value:**

   | k | 0 | 1 | 2 | 3 or more |
   |---|---|---|---|---|
   | value | 1.0 | 0.7 | 0.3 | 0 |

4. **Weight by time:** `S_gap = Σ (gap length / total time) × value(k)`.

**Example.** A 60 s run has 14 gaps of 3 s (42 s), 1 gap of 6 s and 1 gap of 12 s:

```
S_gap = (42/60)·1.0 + (6/60)·0.7 + (12/60)·0 = 0.70 + 0.07 + 0 = 0.77
```

### The straight-line scaling

```
S = (x − bad) / (good − bad), clipped to 0..1
```

**Example:** a map latency of 702 ms gives S_lat = (702 − 3000) / (300 − 3000) = 0.85.

---

## 3. Step 2: the five weighting methods

The worked examples use this small table of 4 runs and 2 criteria:

| Run | map_gap | tf_pdr |
|---|---|---|
| A | 1.0 | 1.0 |
| B | 0.6 | 0.9 |
| C | 0.2 | 0.7 |
| D | 0.9 | 0.95 |

### 3.1 Subjective weights

**What it is:** weights you choose from the project's needs.

**Our values:** map gap 0.50, map latency 0.25, TF PDR 0.15, TF latency 0.10.

**Reasoning:** the map is the stream the base cannot replace, so the two map terms carry 75 %. TF corrects itself with the next sample, so it carries 25 %.

### 3.2 AHP (Analytic Hierarchy Process)

**What it is:** your judgement, made structured and checked for consistency. You compare criteria **two at a time** on a 1–9 scale:

| Value | Meaning |
|---|---|
| 1 | Equally important |
| 3 | Moderately more important |
| 5 | Strongly more important |
| 7 | Very strongly more important |
| 9 | Extremely more important |
| 1/3, 1/5 … | The reverse |

**Our matrix** (row compared with column):

| | map_gap | map_lat | tf_pdr | tf_lat |
|---|---|---|---|---|
| map_gap | 1 | 2 | 3 | 5 |
| map_lat | 1/2 | 1 | 2 | 3 |
| tf_pdr | 1/3 | 1/2 | 1 | 2 |
| tf_lat | 1/5 | 1/3 | 1/2 | 1 |

**Steps:**
1. Find the largest eigenvalue λmax of the matrix and its eigenvector. The eigenvector, scaled to sum to 1, gives the weights.
2. Check consistency:
   - Consistency index: `CI = (λmax − n) / (n − 1)`.
   - Consistency ratio: `CR = CI / RI`, where RI is a table value (0.90 for n = 4).
3. **CR < 0.10 means the judgements are consistent.** Ours is 0.005. If CR is too high, some comparisons contradict each other (for example A > B and B > C, but C > A), and the matrix should be revised.

**Result:** 0.48 / 0.27 / 0.16 / 0.09, close to our subjective weights. AHP confirms them.

### 3.3 CRITIC (CRiteria Importance Through Intercriteria Correlation)

**What it is:** a criterion gets more weight if it **varies a lot** (contrast) and **disagrees with the others** (conflict).

**Formula:**
```
C_j = σ_j × Σ_k (1 − r_jk)          w_j = C_j / Σ C
```
Here σ_j is the standard deviation of criterion j, and r_jk is its correlation with criterion k.

**Worked example:**
- Standard deviations: σ(map_gap) = 0.311, σ(tf_pdr) = 0.114.
- Correlation between them: r = 0.979, so each has a conflict of 1 − 0.979 = 0.021.
- C(map_gap) = 0.311 × 0.021 = 0.0065 and C(tf_pdr) = 0.114 × 0.021 = 0.0024.
- **Weights:** map_gap = 0.73, tf_pdr = 0.27. Map gap varies about three times as much, so it gets about three times the weight.

### 3.4 Entropy

**What it is:** from information theory. If a criterion's values are spread **unevenly** across runs, it tells runs apart well, so it carries more information and gets more weight. If all runs have nearly the same value, it carries no information.

**Steps:**
1. Share of each run: `p_ij = x_ij / Σ_i x_ij`
2. Entropy: `e_j = −(1 / ln m) × Σ_i p_ij ln p_ij` (m = number of runs; e ranges 0–1)
3. Divergence: `d_j = 1 − e_j`
4. Weight: `w_j = d_j / Σ d`

**Worked example:**
- e(map_gap) = 0.910, so d = 0.090.
- e(tf_pdr) = 0.994, so d = 0.006 (its values are nearly even).
- **Weights:** map_gap = 0.94, tf_pdr = 0.06.

Entropy reacts most strongly to uneven spread, which is why it gives such an extreme split.

### 3.5 MEREC (MEthod based on the Removal Effects of Criteria)

**What it is:** remove one criterion at a time and see how much each run's overall performance changes. A criterion whose removal changes a lot gets more weight.

**Steps:**
1. Normalise each value against the best run: `n_ij = min_i(x_ij) / x_ij`
2. Overall performance of each run: `S_i = ln(1 + mean_j |ln n_ij|)`
3. The same, with criterion j removed: `S'_ij`
4. Removal effect: `E_j = Σ_i |S'_ij − S_i|`
5. Weight: `w_j = E_j / Σ E`

**Worked example result:** map_gap = 0.58, tf_pdr = 0.42.

MEREC is the most sensitive of the three to small values. On our field data it put map latency first (0.43), because one-hop map latency ranges widely (206–702 ms).

### 3.6 Which to trust

| Method | Based on | Strength | Weakness |
|---|---|---|---|
| Subjective | Project needs | Reflects importance | Needs justification |
| AHP | Structured judgement | Checks consistency (CR) | Still judgement |
| CRITIC | Spread + correlation | Removes overlap between criteria | Rewards variation, not importance |
| Entropy | Uneven spread | Simple | Very extreme with few runs |
| MEREC | Removal effect | Looks at all criteria together | Very sensitive to small values |

**Rule used in this project:** use the subjective weights, confirm them with AHP (CR < 0.10), and report CRITIC, Entropy and MEREC as a cross-check. If the objective methods rank the most important criterion first, that is extra support. If they don't, explain why (usually a criterion that barely varied in the data).

---

## 4. Step 3: scores and sensitivity

- **Scores.** For each weight set, `Q = Σ w_j × S_j` per scenario. If every weight set ranks the scenarios in nearly the same order, the conclusion doesn't depend on the weighting choice.
- **Sensitivity.** Each subjective weight is changed by −20 % and +20 % in turn (then all weights rescaled to sum to 1), plus 2,000 random combinations within ±20 %. For each change the program reports:
  - **Kendall τ** between the new ranking and the original. 1.0 means identical; above 0.9 means very stable.
  - **Max rank shift:** the furthest any scenario moved.

On the field data, τ stayed at or above 0.97, and no scenario moved more than 2 places.

---

## 5. How to run it

**Needs:** Python 3.9+, `numpy`, `pandas`, `scipy` (`pip install numpy pandas scipy`).

### Mode 1: raw mesh logs (`mesh`)

Use this mode for files written by the base-station receiver. It needs these columns:

```
timestamp, scenario_id, run_id, map_active,
map_latency_avg_ms, tf_pdr_percent, tf_latency_avg_ms
```

Other columns are ignored. Several files can be given at once.

```bash
python3 weights_calculator.py mesh mesh_runs_hops_rssi.csv mesh_runs_hops_rssi_scen31plus.csv --exclude 6 7 8 42
```

`--exclude` leaves out scenarios. Runs shorter than 30 rows are left out of the objective weights, but still count in the scores.

### Mode 2: any decision matrix (`matrix`)

Use this mode for any table with one row per alternative (a run, a scenario, a test) and one column per criterion.

```bash
python3 weights_calculator.py matrix example_matrix.csv --id run \
        --benefit map_delivery tf_pdr_mean --cost map_lat_med tf_lat_med
```

- `--benefit`: higher is better (PDR, delivery, throughput).
- `--cost`: lower is better (latency, jitter, gap).
- Each column is min-max scaled to 0–1 (1 = best) before weighting.
- Subjective weights and AHP apply only if `--config` gives them for exactly these column names.

### Changing settings (`--config`)

Put only the settings you want to change in a JSON file. Everything else keeps its default.

```json
{
  "subjective": {"map_gap": 0.5, "map_lat": 0.25, "tf_pdr": 0.15, "tf_lat": 0.10},
  "k_value": {"0": 1.0, "1": 0.7, "2": 0.3, "3": 0.0},
  "anchors": {"map_lat": [300, 3000], "tf_pdr": [99, 85], "tf_lat": [100, 1000]},
  "min_rows_per_run": 30,
  "sensitivity": {"change": 0.20, "trials": 2000, "seed": 0}
}
```

```bash
python3 weights_calculator.py --config my_settings.json --out results mesh data.csv
```

For a new criterion set in matrix mode, also give `"ahp": {"criteria": [...], "matrix": [[...]]}` with one row and column per criterion.

### Outputs (in `--out`, default `weights_out/`)

| File | Contents |
|---|---|
| `weights.csv` | Weights from every method, one column each |
| `scores.csv` | Q per scenario (or row) for every weight set, plus max k in mesh mode |
| `sensitivity.csv` | Kendall τ and max rank shift for each ±20 % test |
| `criteria_per_run.csv` | The 0–1 criteria for every run, so each score can be traced back |

---

## 6. Check against the project results

Running mesh mode on the two field files with `--exclude 6 7 8 42` reproduces the numbers in the field-test report:

| | Subjective | AHP | CRITIC | Entropy | MEREC |
|---|---|---|---|---|---|
| map_gap | 0.50 | 0.483 | 0.433 | 0.514 | 0.183 |
| map_lat | 0.25 | 0.272 | 0.153 | 0.054 | 0.433 |
| tf_pdr | 0.15 | 0.157 | 0.227 | 0.243 | 0.187 |
| tf_lat | 0.10 | 0.088 | 0.187 | 0.189 | 0.197 |

AHP CR = 0.005. Sensitivity: worst-case Kendall τ = 0.966, max rank shift = 2.

---

## 7. Cautions

- **Few runs make objective weights unstable.** With 13 one-hop runs only, Entropy gives map gap 0.65 and MEREC 0.51. With all 49 runs, MEREC drops to 0.18. Report how many runs went in.
- **A criterion that never varies gets almost no objective weight.** That says nothing about how much it matters.
- **Overlapping criteria double-count.** Check correlations first and drop one of any pair above about 0.8 (as we did with combined PDR and TF PDR, ρ = 1.00).
- **Q is an average.** Always report the maximum k next to Q, because a short failure can hide inside a good average.
