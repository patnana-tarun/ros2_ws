#!/usr/bin/env python3
"""
weights_calculator.py — weights for the communication-quality score Q.

Two ways to use it
------------------
1) MESH mode (raw one-second logs, as written by the base-station receiver):

     python3 weights_calculator.py mesh  file1.csv [file2.csv ...]  [--exclude 6 7 8 42]

   The script turns the raw rows into four 0..1 criteria per run
   (S_gap, S_lat, S_tfpdr, S_tflat), then computes weights with
   AHP, CRITIC, Entropy and MEREC, scores every scenario, and runs a
   +/-20 % sensitivity check.

   Columns it needs:
     timestamp, scenario_id, run_id, map_active,
     map_latency_avg_ms, tf_pdr_percent, tf_latency_avg_ms

2) MATRIX mode (any decision matrix: one row per alternative, one column per criterion):

     python3 weights_calculator.py matrix  table.csv  --id run \
             --benefit map_delivery tf_pdr  --cost map_latency tf_latency

   "benefit" = higher is better, "cost" = lower is better.
   Each column is min-max scaled to 0..1 (1 = best) and then weighted.

Settings (anchors, k values, subjective weights, AHP matrix) live in DEFAULTS
below, or in a JSON file passed with --config (any key you leave out keeps its default).

Outputs go to --out (default ./weights_out): weights.csv, criteria_per_run.csv,
scores.csv, sensitivity.csv.  Everything is also printed.

Needs: python 3.9+, numpy, pandas, scipy.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

# ----------------------------------------------------------------------------- settings
DEFAULTS = {
    "map_period_s": 3.0,                     # one map every 3 s
    "k_value": {"0": 1.0, "1": 0.7, "2": 0.3, "3": 0.0},   # value of k maps missed in a row (3 = 3 or more)
    "edge_gap_ignore_s": 4.0,                # ignore run-edge gaps shorter than this
    "anchors": {                             # [value scoring 1, value scoring 0]
        "map_lat": [300, 3000],              # ms, median map latency
        "tf_pdr": [99, 85],                  # %,  mean TF PDR
        "tf_lat": [100, 1000],               # ms, median TF latency
    },
    "fill_missing": {"map_lat": 3000, "tf_lat": 1000},  # a run with no value at all
    "min_rows_per_run": 30,                  # shorter runs are left out of the objective weights
    "subjective": {"map_gap": 0.50, "map_lat": 0.25, "tf_pdr": 0.15, "tf_lat": 0.10},
    "ahp": {                                 # pairwise judgements, Saaty 1-9 scale
        "criteria": ["map_gap", "map_lat", "tf_pdr", "tf_lat"],
        # row i vs column j: how much more important i is than j
        "matrix": [[1, 2, 3, 5],
                   [1 / 2, 1, 2, 3],
                   [1 / 3, 1 / 2, 1, 2],
                   [1 / 5, 1 / 3, 1 / 2, 1]],
    },
    "sensitivity": {"change": 0.20, "trials": 2000, "seed": 0},
}

CRITERIA = ["map_gap", "map_lat", "tf_pdr", "tf_lat"]
RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def load_config(path):
    cfg = json.loads(json.dumps(DEFAULTS))          # deep copy
    if path:
        with open(path) as f:
            user = json.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


# ----------------------------------------------------------------------------- step 1: raw rows -> criteria
def linear(x, good, bad):
    """1 at `good`, 0 at `bad`, straight line between, clipped to 0..1."""
    return float(np.clip((x - bad) / (good - bad), 0.0, 1.0))


def map_gaps(run, period):
    """Gaps between maps in one run, from timestamps. Edge gaps are flagged."""
    t = run["timestamp"].to_numpy()
    t_maps = run.loc[run["map_active"] == 1, "timestamp"].to_numpy()
    start, end = t[0], t[-1] + 1.0
    if len(t_maps) == 0:
        return [(end - start, True)]
    gaps = [(t_maps[0] - start, True)]
    gaps += [(b - a, False) for a, b in zip(t_maps[:-1], t_maps[1:])]
    gaps.append((end - t_maps[-1], True))
    return gaps


def gap_score(gaps, cfg):
    """Time-weighted value of missed maps: sum(share of time at k) * value(k)."""
    period = cfg["map_period_s"]
    kv = {int(k): v for k, v in cfg["k_value"].items()}
    used = [(g, e) for g, e in gaps if not (e and g < cfg["edge_gap_ignore_s"])]
    total = sum(g for g, _ in used)
    if total == 0:
        return 1.0, 0
    score, max_k = 0.0, 0
    for g, _ in used:
        k = int(max(round(g / period) - 1, 0))
        max_k = max(max_k, k)
        score += g / total * kv[min(k, 3)]
    return score, max_k


def criteria_for(rows, cfg):
    """The four 0..1 criteria for one group of rows (a run, or a whole scenario)."""
    gaps = []
    for _, run in rows.groupby("run_id"):
        gaps += map_gaps(run.sort_values("timestamp"), cfg["map_period_s"])
    s_gap, max_k = gap_score(gaps, cfg)
    a, f = cfg["anchors"], cfg["fill_missing"]
    map_lat = rows["map_latency_avg_ms"].median()
    tf_lat = rows["tf_latency_avg_ms"].median()
    tf_pdr = rows["tf_pdr_percent"].fillna(0).mean()      # empty = outage = 0 %
    return {
        "map_gap": s_gap,
        "map_lat": linear(f["map_lat"] if pd.isna(map_lat) else map_lat, *a["map_lat"]),
        "tf_pdr": linear(tf_pdr, *a["tf_pdr"]),
        "tf_lat": linear(f["tf_lat"] if pd.isna(tf_lat) else tf_lat, *a["tf_lat"]),
        "max_k": max_k,
        "rows": len(rows),
    }


def build_criteria(df, cfg):
    need = ["timestamp", "scenario_id", "run_id", "map_active",
            "map_latency_avg_ms", "tf_pdr_percent", "tf_latency_avg_ms"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        sys.exit(f"Missing columns: {missing}")
    per_run = pd.DataFrame([{"scenario_id": s, "run_id": r, **criteria_for(g, cfg)}
                            for (s, r), g in df.groupby(["scenario_id", "run_id"])])
    per_scen = pd.DataFrame([{"scenario_id": s, **criteria_for(g, cfg)}
                             for s, g in df.groupby("scenario_id")]).set_index("scenario_id")
    return per_run, per_scen


# ----------------------------------------------------------------------------- step 2: weighting methods
# All four take X = alternatives x criteria, values 0..1, higher = better.

def ahp(cfg):
    """Weights = principal eigenvector of the pairwise matrix. CR < 0.10 is acceptable."""
    A = np.array(cfg["ahp"]["matrix"], float)
    n = len(A)
    vals, vecs = np.linalg.eig(A)
    i = int(np.argmax(vals.real))
    w = np.abs(vecs[:, i].real)
    w /= w.sum()
    ci = (vals[i].real - n) / (n - 1) if n > 1 else 0.0
    ri = RANDOM_INDEX.get(n, 1.49)
    cr = ci / ri if ri else 0.0
    return pd.Series(w, index=cfg["ahp"]["criteria"]), cr


def critic(X):
    """CRITIC: contrast (std dev) x conflict (1 - correlation with the others)."""
    sd = X.std(ddof=0)
    r = X.corr().fillna(0)
    c = sd * (1 - r).sum()
    return c / c.sum()


def entropy(X):
    """Entropy: criteria whose values are spread unevenly carry more information."""
    P = (X + 1e-9) / (X + 1e-9).sum()
    e = -(P * np.log(P)).sum() / np.log(len(X))
    d = 1 - e
    return d / d.sum()


def merec(X):
    """MEREC: how much the overall performance changes when one criterion is removed."""
    Y = X.clip(lower=1e-3)
    N = Y.min() / Y                                  # benefit criteria
    S = np.log(1 + np.abs(np.log(N)).mean(axis=1))
    E = {}
    for j in N.columns:
        Sj = np.log(1 + np.abs(np.log(N.drop(columns=j))).mean(axis=1))
        E[j] = (Sj - S).abs().sum()
    E = pd.Series(E)
    return E / E.sum()


def all_weights(X, cfg, with_ahp=True):
    cols = {}
    if "subjective" in cfg and set(cfg["subjective"]) == set(X.columns):
        s = pd.Series(cfg["subjective"])
        cols["subjective"] = s / s.sum()
    cr = None
    if with_ahp and set(cfg["ahp"]["criteria"]) == set(X.columns):
        cols["AHP"], cr = ahp(cfg)
    cols["CRITIC"] = critic(X)
    cols["Entropy"] = entropy(X)
    cols["MEREC"] = merec(X)
    return pd.DataFrame(cols).loc[X.columns], cr


# ----------------------------------------------------------------------------- step 3: scores and sensitivity
def scores(C, W):
    return pd.DataFrame({m: C[W.index] @ W[m] for m in W.columns})


def sensitivity(C, w, cfg):
    sc = cfg["sensitivity"]
    base = (C[w.index] @ w).rank(ascending=False)
    rows = []
    for j in w.index:
        for f in (1 - sc["change"], 1 + sc["change"]):
            w2 = w.copy()
            w2[j] *= f
            w2 /= w2.sum()
            r = (C[w.index] @ w2).rank(ascending=False)
            rows.append({"test": f"{j} x{f:.2f}", "kendall_tau": kendalltau(base, r)[0],
                         "max_rank_shift": int((r - base).abs().max())})
    rng = np.random.default_rng(sc["seed"])
    taus, shifts = [], []
    for _ in range(sc["trials"]):
        w2 = w * rng.uniform(1 - sc["change"], 1 + sc["change"], len(w))
        w2 /= w2.sum()
        r = (C[w.index] @ w2).rank(ascending=False)
        taus.append(kendalltau(base, r)[0])
        shifts.append((r - base).abs().max())
    rows.append({"test": f"random +/-{sc['change']:.0%} ({sc['trials']} trials), worst case",
                 "kendall_tau": float(np.min(taus)), "max_rank_shift": int(np.max(shifts))})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- modes
def run_mesh(args, cfg):
    df = pd.concat([pd.read_csv(p) for p in args.files], ignore_index=True)
    if args.exclude:
        df = df[~df["scenario_id"].isin(args.exclude)]
    per_run, per_scen = build_criteria(df, cfg)
    X = per_run.loc[per_run["rows"] >= cfg["min_rows_per_run"], CRITERIA].reset_index(drop=True)
    W, cr = all_weights(X, cfg)
    S = scores(per_scen, W).join(per_scen[["max_k"]])
    base = "subjective" if "subjective" in W else W.columns[0]
    sens = sensitivity(per_scen, W[base], cfg)
    report(W, cr, S, sens, args.out, per_run, f"{len(X)} runs used for the objective weights")


def run_matrix(args, cfg):
    df = pd.read_csv(args.file)
    ids = df[args.id] if args.id else pd.Series(range(len(df)))
    cols = (args.benefit or []) + (args.cost or [])
    if not cols:
        sys.exit("Give at least one --benefit or --cost column.")
    X = df[cols].astype(float).copy()
    for c in cols:                                   # min-max to 0..1, 1 = best
        lo, hi = X[c].min(), X[c].max()
        span = (hi - lo) or 1.0
        X[c] = (X[c] - lo) / span if c in (args.benefit or []) else (hi - X[c]) / span
    X.index = ids
    W, cr = all_weights(X, cfg, with_ahp=set(cfg["ahp"]["criteria"]) == set(cols))
    S = scores(X, W)
    sens = sensitivity(X, W[W.columns[0]], cfg)
    report(W, cr, S, sens, args.out, X.reset_index(), f"{len(X)} rows, criteria: {cols}")


def report(W, cr, S, sens, out, criteria_table, note):
    os.makedirs(out, exist_ok=True)
    W.to_csv(os.path.join(out, "weights.csv"))
    S.to_csv(os.path.join(out, "scores.csv"))
    sens.to_csv(os.path.join(out, "sensitivity.csv"), index=False)
    criteria_table.to_csv(os.path.join(out, "criteria_per_run.csv"), index=False)
    pd.set_option("display.width", 200)
    print(f"\n{note}\n\nWEIGHTS\n{W.round(3)}")
    if cr is not None:
        print(f"\nAHP consistency ratio CR = {cr:.3f} ({'OK' if cr < 0.10 else 'TOO HIGH: revise the pairwise matrix'})")
    print(f"\nSCORES (Q per scenario / alternative, one column per weight set)\n{S.round(3)}")
    print(f"\nSENSITIVITY\n{sens.round(3).to_string(index=False)}")
    print(f"\nFiles written to {os.path.abspath(out)}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="JSON file overriding DEFAULTS")
    p.add_argument("--out", default="weights_out")
    sub = p.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("mesh", help="raw one-second mesh logs")
    m.add_argument("files", nargs="+")
    m.add_argument("--exclude", nargs="*", type=int, default=[], help="scenario ids to leave out")
    x = sub.add_parser("matrix", help="any decision matrix")
    x.add_argument("file")
    x.add_argument("--id", help="column naming each row")
    x.add_argument("--benefit", nargs="*", help="higher is better")
    x.add_argument("--cost", nargs="*", help="lower is better")
    args = p.parse_args()
    cfg = load_config(args.config)
    run_mesh(args, cfg) if args.mode == "mesh" else run_matrix(args, cfg)


if __name__ == "__main__":
    main()
