"""
Frontier-selection policies under comparison.

Every policy receives an IDENTICAL candidate list - same map, same pose, same
frontier clusters, same per-candidate features - and returns the index of the
frontier it selects. The selection rule is therefore the only variable that
differs between arms of the experiment.

Candidate features (computed once, shared by all policies):
    d     Euclidean robot-to-centroid distance                     [m]
    a     area of the bordering unknown region                     [m^2]
    t     trapezoid indicator in {-1, 0, +1}                       [-]
    cells number of frontier cells in the cluster                  [-]

References
----------
NF      Yamauchi, B. (1997). A frontier-based approach for autonomous
        exploration. IEEE CIRA, 146-151.
CU      Gonzalez-Banos, H. & Latombe, J.-C. (2002). Navigation strategies for
        exploring indoor environments. IJRR 21(10-11), 829-848.
MIG/LF  Common greedy information-gain baselines as surveyed in Holz, D.,
        Basilico, N., Amigoni, F. & Behnke, S. (2010). Evaluating the
        efficiency of frontier-based exploration strategies. ISR/ROBOTIK.
TAD     Buriboev, A., Choi, J. & Jeon, H. (2025). Optimized frontier-based
        path planning using the TAD algorithm. Electronics 14(1), 74.
"""

import numpy as np


def _norm(vals):
    """Min-max normalisation; constant vectors map to all-ones.

    This mirrors the production node exactly (verified in the validation
    dossier, assertion V2.6) so the TAD arm is the real algorithm.
    """
    v = np.asarray(vals, dtype=float)
    lo, hi = v.min(), v.max()
    return np.ones_like(v) if hi - lo < 1e-6 else (v - lo) / (hi - lo)


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

def random_frontier(cands, rng, **kw):
    """Uniform random choice. Control arm: establishes the noise floor that
    any purposeful strategy must beat to justify its existence."""
    return int(rng.randint(len(cands)))


def nearest_frontier(cands, rng, **kw):
    """NF - Yamauchi (1997). Always the closest frontier."""
    return int(np.argmin([c['d'] for c in cands]))


def largest_frontier(cands, rng, **kw):
    """LF - greedy on frontier extent. Cluster size is a cheap proxy for how
    much boundary is available to reveal."""
    return int(np.argmax([c['cells'] for c in cands]))


def max_information_gain(cands, rng, **kw):
    """MIG - greedy on expected information gain, measured as the area of the
    unknown region the frontier borders. Ignores travel cost entirely."""
    return int(np.argmax([c['a'] for c in cands]))


def cost_utility_exp(cands, rng, lam=0.3, **kw):
    """CU-exp - Gonzalez-Banos & Latombe (2002).

        U_n = A_n * exp(-lambda * d_n)

    Information gain discounted multiplicatively by travel cost. lambda is a
    tuned hyperparameter (see benchmark.tune_hyperparameters)."""
    a = np.array([c['a'] for c in cands], dtype=float)
    d = np.array([c['d'] for c in cands], dtype=float)
    return int(np.argmax(a * np.exp(-lam * d)))


def cost_utility_linear(cands, rng, lam=0.5, **kw):
    """CU-lin - additive cost-utility trade-off on normalised terms:

        U_n = norm(A_n) - lambda * norm(d_n)

    The additive counterpart to CU-exp; normalisation keeps lambda
    dimensionless and comparable across maps."""
    a = _norm([c['a'] for c in cands])
    d = _norm([c['d'] for c in cands])
    return int(np.argmax(a - lam * d))


# ---------------------------------------------------------------------------
# The algorithm under assessment
# ---------------------------------------------------------------------------

def tad(cands, rng, w_d=1.0, w_a=1.0, w_t=1.0, **kw):
    """TAD - Buriboev, Choi & Jeon (2025), as implemented in this project.

        F_n = w_d*norm(d_n) + w_a*norm(a_n) + w_t*norm(t_n)

    Identical formulation to frontier_tad_node.py; equivalence between that
    node and this expression is established in the validation dossier (V4,
    200/200 exact agreement)."""
    d = _norm([c['d'] for c in cands])
    a = _norm([c['a'] for c in cands])
    t = _norm([c['t'] for c in cands])
    return int(np.argmax(w_d * d + w_a * a + w_t * t))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

POLICIES = {
    'Random':  dict(fn=random_frontier,     params={},                 tunable=None,
                    cite='control arm'),
    'NF':      dict(fn=nearest_frontier,    params={},                 tunable=None,
                    cite='Yamauchi 1997'),
    'LF':      dict(fn=largest_frontier,    params={},                 tunable=None,
                    cite='greedy extent'),
    'MIG':     dict(fn=max_information_gain, params={},                tunable=None,
                    cite='greedy info-gain'),
    'CU-exp':  dict(fn=cost_utility_exp,    params=dict(lam=0.3),      tunable='lam',
                    cite='Gonzalez-Banos & Latombe 2002'),
    'CU-lin':  dict(fn=cost_utility_linear, params=dict(lam=0.5),      tunable='lam',
                    cite='additive cost-utility'),
    'TAD':     dict(fn=tad, params=dict(w_d=1.0, w_a=1.0, w_t=1.0),    tunable=None,
                    cite='Buriboev et al. 2025 (as implemented)'),
    'TAD-tuned': dict(fn=tad, params=dict(w_d=1.0, w_a=1.0, w_t=1.0),  tunable='weights',
                      cite='this work, weights tuned on held-out seeds'),
}
