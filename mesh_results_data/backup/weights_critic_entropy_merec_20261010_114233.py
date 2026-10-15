"""
Objective weighting of mesh-network QoS criteria
Criteria : Throughput, Latency, PDR
Methods  : CRITIC, Entropy (Shannon), MEREC
Data     : mesh_runs_normalized.csv  (scenarios 8, 10, 11 excluded)

All three normalized columns (pdr_n, latency_n, throughput_n) are already
benefit-type in [0, 1]  (latency_n is inverted: higher = lower latency = better).

Usage:  python weights_critic_entropy_merec.py [path/to/mesh_runs_normalized.csv]
"""

import sys
import numpy as np
import pandas as pd

CSV = sys.argv[1] if len(sys.argv) > 1 else "mesh_runs_normalized.csv"
EXCLUDE = [8, 10, 11]

# Normalized columns (used by CRITIC and Entropy)
NORM_COLS = {"Throughput": "throughput_n", "Latency": "latency_n", "PDR": "pdr_n"}
# Raw columns + criterion type (used by MEREC, which has its own normalization)
RAW_COLS = {
    "Throughput": ("throughput_kbytes_per_sec", "benefit"),
    "Latency":    ("latency_avg_ms",            "cost"),
    "PDR":        ("pdr_percent",               "benefit"),
}


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------
def load_data(path):
    df = pd.read_csv(path)
    n_all = len(df)
    df = df[~df["scenario_id"].isin(EXCLUDE)]
    present = sorted(set(EXCLUDE) & set(pd.read_csv(path)["scenario_id"]))
    needed = list(NORM_COLS.values()) + [c for c, _ in RAW_COLS.values()]
    n_before_na = len(df)
    df = df.dropna(subset=needed).reset_index(drop=True)
    print(f"Rows in file            : {n_all}")
    print(f"Excluded scenarios      : {EXCLUDE} (present in file: {present})")
    print(f"Rows after exclusion    : {n_before_na}")
    print(f"Rows dropped (missing)  : {n_before_na - len(df)}")
    print(f"Rows used (m)           : {len(df)}")
    print(f"Scenarios used          : {sorted(df['scenario_id'].unique().tolist())}\n")
    return df


# ----------------------------------------------------------------------
# 1. CRITIC  (Diakoulaki et al., 1995)
#    sigma_j : standard deviation of criterion j      (contrast intensity)
#    r_jk    : Pearson correlation between j and k    (conflict)
#    C_j     = sigma_j * sum_k (1 - r_jk)             (information content)
#    w_j     = C_j / sum_j C_j
# ----------------------------------------------------------------------
def critic(X):
    sigma = X.std(axis=0, ddof=1)
    R = np.corrcoef(X, rowvar=False)
    conflict = (1 - R).sum(axis=0)
    C = sigma * conflict
    w = C / C.sum()
    return w, {"sigma": sigma, "conflict": conflict, "C": C, "R": R}


# ----------------------------------------------------------------------
# 2. Entropy weight method (Shannon)
#    p_ij = x_ij / sum_i x_ij
#    E_j  = -(1 / ln m) * sum_i p_ij ln p_ij    (with 0 * ln 0 = 0)
#    d_j  = 1 - E_j                              (degree of divergence)
#    w_j  = d_j / sum_j d_j
# ----------------------------------------------------------------------
def entropy(X):
    m = X.shape[0]
    P = X / X.sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        plogp = np.where(P > 0, P * np.log(P), 0.0)
    E = -plogp.sum(axis=0) / np.log(m)
    d = 1 - E
    w = d / d.sum()
    return w, {"E": E, "d": d}


# ----------------------------------------------------------------------
# 3. MEREC – Method based on the Removal Effects of Criteria
#    (Keshavarz-Ghorabaee et al., 2021)
#    Step 1 normalization (all values must be > 0):
#        benefit: n_ij = min_k x_kj / x_ij
#        cost   : n_ij = x_ij / max_k x_kj
#    Step 2 overall performance:
#        S_i  = ln(1 + (1/n) * sum_j |ln n_ij|)
#    Step 3 performance with criterion j removed:
#        S'_ij = ln(1 + (1/n) * sum_{k != j} |ln n_ik|)
#    Step 4 removal effect:
#        E_j  = sum_i |S'_ij - S_i|
#    Step 5 weights:
#        w_j  = E_j / sum_j E_j
# ----------------------------------------------------------------------
def merec(X, types):
    if (X <= 0).any():
        raise ValueError("MEREC needs strictly positive values.")
    m, n = X.shape
    N = np.empty_like(X, dtype=float)
    for j, t in enumerate(types):
        col = X[:, j]
        N[:, j] = col.min() / col if t == "benefit" else col / col.max()
    absln = np.abs(np.log(N))
    S = np.log(1 + absln.sum(axis=1) / n)
    S_rem = np.empty((m, n))
    for j in range(n):
        S_rem[:, j] = np.log(1 + (absln.sum(axis=1) - absln[:, j]) / n)
    E = np.abs(S_rem - S[:, None]).sum(axis=0)
    w = E / E.sum()
    return w, {"E": E}


# ----------------------------------------------------------------------
def show(title, names, w, extras):
    print("=" * 60)
    print(title)
    print("=" * 60)
    tab = pd.DataFrame({k: v for k, v in extras.items() if np.ndim(v) == 1},
                       index=names)
    tab["Weight"] = w
    tab["Rank"] = tab["Weight"].rank(ascending=False).astype(int)
    print(tab.round(6).to_string(), "\n")


def main():
    df = load_data(CSV)
    names = list(NORM_COLS.keys())

    Xn = df[list(NORM_COLS.values())].to_numpy(float)
    w_c, ex_c = critic(Xn)
    print("Correlation matrix (CRITIC):")
    print(pd.DataFrame(ex_c.pop("R"), index=names, columns=names).round(4), "\n")
    show("CRITIC  (normalized data)", names, w_c, ex_c)

    w_e, ex_e = entropy(Xn)
    show("ENTROPY (normalized data)", names, w_e, ex_e)

    Xr = df[[c for c, _ in RAW_COLS.values()]].to_numpy(float)
    types = [t for _, t in RAW_COLS.values()]
    w_m, ex_m = merec(Xr, types)
    show("MEREC   (raw data, MEREC's own normalization)", names, w_m, ex_m)

    summary = pd.DataFrame({"CRITIC": w_c, "Entropy": w_e, "MEREC": w_m},
                           index=names)
    summary["Mean"] = summary.mean(axis=1)
    print("=" * 60)
    print("SUMMARY OF WEIGHTS")
    print("=" * 60)
    print(summary.round(4).to_string())
    summary.round(6).to_csv("criteria_weights.csv", index_label="Criterion")
    print("\nSaved: criteria_weights.csv")


if __name__ == "__main__":
    main()
