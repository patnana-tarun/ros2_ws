"""
Statistical analysis and figures for the policy comparison.

Protocol follows Demsar, J. (2006), "Statistical Comparisons of Classifiers
over Multiple Data Sets", JMLR 7:1-30, which is the standard procedure for
comparing several algorithms across several problem instances:

  1. Friedman test  - omnibus test on mean ranks; is ANY policy different?
  2. Nemenyi post-hoc - all-pairs comparison via a critical difference (CD)
  3. Wilcoxon + Holm  - focused pairwise tests against our method

Ranks rather than raw values are used because absolute metrics are not
commensurable across environments of different size.
"""

import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import stats as sps  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, 'figures')
os.makedirs(FIG, exist_ok=True)

INK = '#1a1a2e'
ACCENT = '#2d6a9f'
OURS = '#b8531f'
GOOD = '#4a7c59'
GREY = '#9a9aa8'

plt.rcParams.update({
    'font.size': 9, 'axes.edgecolor': INK, 'axes.labelcolor': INK,
    'text.color': INK, 'xtick.color': INK, 'ytick.color': INK,
    'axes.spines.top': False, 'axes.spines.right': False,
    'figure.dpi': 200, 'savefig.dpi': 200,
})

# Studentized range statistic / sqrt(2), alpha = 0.05 (Demsar 2006, Table 5)
Q05 = {2: 1.960, 3: 2.343, 4: 2.569, 5: 2.728, 6: 2.850,
       7: 2.949, 8: 3.031, 9: 3.102, 10: 3.164}

OUR_POLICIES = ('TAD', 'TAD-tuned')

data = json.load(open(os.path.join(HERE, 'results_comparison.json')))
runs = data['runs']
POLICY_ORDER = ['Random', 'NF', 'LF', 'MIG', 'CU-exp', 'CU-lin', 'TAD', 'TAD-tuned']
ENVS = list(data['environments'].keys())


def matrix(metric, higher_is_better=True):
    """[blocks x policies] matrix; a block is one (environment, seed) pair."""
    blocks = [(e, s) for e in ENVS for s in data['eval_seeds']]
    idx = {(r['env'], r['seed'], r['policy']): r for r in runs}
    M = np.full((len(blocks), len(POLICY_ORDER)), np.nan)
    for i, (e, s) in enumerate(blocks):
        for j, p in enumerate(POLICY_ORDER):
            r = idx.get((e, s, p))
            if r is not None:
                M[i, j] = r[metric]
    return M, blocks


def ranks_of(M, higher_is_better=True):
    """Average ranks per block; rank 1 = best."""
    X = -M if higher_is_better else M
    R = np.apply_along_axis(sps.rankdata, 1, X)
    return R


def friedman_nemenyi(M, higher_is_better=True):
    ok = ~np.isnan(M).any(axis=1)
    M = M[ok]
    R = ranks_of(M, higher_is_better)
    mean_ranks = R.mean(axis=0)
    stat, p = sps.friedmanchisquare(*[M[:, j] for j in range(M.shape[1])])
    k, N = M.shape[1], M.shape[0]
    cd = Q05[k] * np.sqrt(k * (k + 1) / (6.0 * N))
    return dict(stat=float(stat), p=float(p), mean_ranks=mean_ranks.tolist(),
                cd=float(cd), n_blocks=int(N), k=int(k))


def wilcoxon_holm(M, ref='TAD-tuned', higher_is_better=True):
    j_ref = POLICY_ORDER.index(ref)
    out = {}
    raw = []
    for j, p in enumerate(POLICY_ORDER):
        if j == j_ref:
            continue
        a, b = M[:, j_ref], M[:, j]
        ok = ~(np.isnan(a) | np.isnan(b))
        if np.allclose(a[ok], b[ok]):
            stat, pv = 0.0, 1.0
        else:
            stat, pv = sps.wilcoxon(a[ok], b[ok])
        raw.append((p, float(pv), float(np.mean(a[ok]) - np.mean(b[ok]))))
    # Holm step-down correction
    raw.sort(key=lambda z: z[1])
    m = len(raw)
    prev = 0.0
    for i, (p, pv, diff) in enumerate(raw):
        adj = min(1.0, max(prev, (m - i) * pv))
        prev = adj
        out[p] = dict(p_raw=pv, p_holm=adj, mean_diff=diff,
                      significant=bool(adj < 0.05))
    return out


# ---------------------------------------------------------------------------
def fig_cd_diagram(res, title, fname):
    """Critical-difference diagram (Demsar 2006)."""
    mr = np.array(res['mean_ranks'])
    cd = res['cd']
    order = np.argsort(mr)
    names = [POLICY_ORDER[i] for i in order]
    vals = mr[order]
    k = len(names)

    fig, ax = plt.subplots(figsize=(8.4, 1.5 + 0.19 * k))
    lo, hi = 0.7, k + 0.3
    ax.set_xlim(lo, hi)
    # Crop the unused band below the lowest label instead of leaving whitespace.
    lowest = 0.60 - 0.075 * max(0, (k // 2) - 1)
    ax.set_ylim(lowest - 0.06, 1.0)
    ax.axis('off')

    yaxis = 0.78
    ax.plot([lo, hi], [yaxis, yaxis], color=INK, lw=1.1)
    for t in range(1, k + 1):
        ax.plot([t, t], [yaxis, yaxis + 0.035], color=INK, lw=1.0)
        ax.text(t, yaxis + 0.06, str(t), ha='center', fontsize=8)
    ax.text((lo + hi) / 2, yaxis + 0.16, 'mean rank  (1 = best)',
            ha='center', fontsize=8.5, color=GREY)

    # CD bar
    ax.plot([lo + 0.1, lo + 0.1 + cd], [yaxis + 0.145, yaxis + 0.145],
            color=OURS, lw=2.2)
    ax.text(lo + 0.1 + cd / 2, yaxis + 0.175, f'CD = {cd:.2f}',
            ha='center', fontsize=8, color=OURS)

    left = [i for i in range(k) if i < k / 2]
    for rank_i, name in enumerate(names):
        v = vals[rank_i]
        is_ours = name in OUR_POLICIES
        col = OURS if is_ours else INK
        side_y = 0.60 - 0.075 * (rank_i if rank_i in left else (k - 1 - rank_i))
        if rank_i in left:
            ax.plot([v, v], [yaxis, side_y], color=col, lw=0.9)
            ax.plot([v, lo + 0.05], [side_y, side_y], color=col, lw=0.9)
            ax.text(lo + 0.02, side_y, f'{name}  ({v:.2f})', ha='right',
                    va='center', fontsize=8.4, color=col,
                    fontweight='bold' if is_ours else 'normal')
        else:
            ax.plot([v, v], [yaxis, side_y], color=col, lw=0.9)
            ax.plot([v, hi - 0.05], [side_y, side_y], color=col, lw=0.9)
            ax.text(hi - 0.02, side_y, f'({v:.2f})  {name}', ha='left',
                    va='center', fontsize=8.4, color=col,
                    fontweight='bold' if is_ours else 'normal')

    # cliques: groups not significantly different
    ypos = yaxis - 0.045
    used = []
    for i in range(k):
        j = i
        while j + 1 < k and vals[j + 1] - vals[i] <= cd:
            j += 1
        if j > i and not any(a <= i and j <= b for a, b in used):
            used.append((i, j))
            ax.plot([vals[i] - 0.03, vals[j] + 0.03], [ypos, ypos],
                    color=GREY, lw=3.0, solid_capstyle='butt')
            ypos -= 0.035

    ax.set_title(title, fontsize=9.5, color=INK, pad=2)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, fname), bbox_inches='tight')
    plt.close(fig)


def fig_coverage_curves():
    """Mean coverage as a function of distance travelled, per policy."""
    fig, axes = plt.subplots(1, len(ENVS), figsize=(12.2, 3.5), sharey=True)
    for ax, env in zip(np.atleast_1d(axes), ENVS):
        budget = data['environments'][env][5]
        grid = np.linspace(0, budget, 160)
        for p in POLICY_ORDER:
            curves = []
            for r in runs:
                if r['policy'] != p or r['env'] != env:
                    continue
                tr = np.array(r['trace'])
                d, c = tr[:, 0], tr[:, 1]
                curves.append(np.interp(grid, d, c, left=c[0], right=c[-1]))
            if not curves:
                continue
            m = np.mean(curves, axis=0)
            is_ours = p in OUR_POLICIES
            ax.plot(grid, m, lw=2.0 if is_ours else 1.1,
                    color=OURS if p == 'TAD' else (GOOD if p == 'TAD-tuned' else None),
                    alpha=1.0 if is_ours else 0.75,
                    label=p, zorder=3 if is_ours else 2)
        ax.set_xlabel('distance travelled (m)')
        ax.set_title(env, fontsize=9)
        ax.grid(alpha=0.13)
    np.atleast_1d(axes)[0].set_ylabel('map coverage (%)')
    np.atleast_1d(axes)[-1].legend(fontsize=7.0, frameon=False, loc='lower right')
    fig.suptitle('Coverage attained per metre travelled  (mean over 20 seeds; '
                 'higher and earlier is better)', fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'coverage_curves.png'), bbox_inches='tight')
    plt.close(fig)


def fig_summary_bars(summary):
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.4))
    panels = [('auc', 'Exploration efficiency (AUC)', True),
              ('distance_m', 'Distance to finish (m)', False),
              ('final_coverage', 'Final coverage (%)', True)]
    for ax, (metric, title, hib) in zip(axes, panels):
        means = [summary[p][metric]['mean'] for p in POLICY_ORDER]
        errs = [summary[p][metric]['ci'] for p in POLICY_ORDER]
        cols = [OURS if p == 'TAD' else GOOD if p == 'TAD-tuned' else GREY
                for p in POLICY_ORDER]
        y = np.arange(len(POLICY_ORDER))
        ax.barh(y, means, xerr=errs, color=cols, edgecolor=INK, linewidth=0.6,
                height=0.62, error_kw=dict(ecolor=INK, lw=0.9), capsize=2.5)
        ax.set_yticks(y)
        ax.set_yticklabels(POLICY_ORDER, fontsize=8)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=9)
        ax.grid(axis='x', alpha=0.13)
    fig.suptitle('Aggregate performance over 60 paired trials '
                 '(3 environments x 20 seeds); bars are 95% CI', fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'summary_bars.png'), bbox_inches='tight')
    plt.close(fig)


def ci95(xs):
    xs = np.asarray(xs, float)
    xs = xs[~np.isnan(xs)]
    if len(xs) < 2:
        return 0.0
    return float(sps.t.ppf(0.975, len(xs) - 1) * xs.std(ddof=1) / np.sqrt(len(xs)))


def main():
    summary = {}
    for p in POLICY_ORDER:
        sub = [r for r in runs if r['policy'] == p]
        summary[p] = {}
        for metric in ('auc', 'distance_m', 'final_coverage', 'turns',
                       'goals', 'time_s', 'decision_ms_mean'):
            xs = [r[metric] for r in sub]
            summary[p][metric] = dict(mean=float(np.mean(xs)),
                                      std=float(np.std(xs, ddof=1)),
                                      ci=ci95(xs))
        d50 = [r['dist_to_50'] for r in sub]
        d75 = [r['dist_to_75'] for r in sub]
        summary[p]['dist_to_50'] = dict(
            mean=float(np.nanmean(d50)), ci=ci95(d50),
            censored=int(np.sum(np.isnan(d50))))
        summary[p]['dist_to_75'] = dict(
            mean=float(np.nanmean(d75)), ci=ci95(d75),
            censored=int(np.sum(np.isnan(d75))))

    tests = {}
    for metric, hib in (('auc', True), ('distance_m', False),
                        ('final_coverage', True), ('turns', False)):
        M, _ = matrix(metric)
        res = friedman_nemenyi(M, hib)
        res['wilcoxon_holm_vs_TAD_tuned'] = wilcoxon_holm(M, 'TAD-tuned', hib)
        res['wilcoxon_holm_vs_TAD'] = wilcoxon_holm(M, 'TAD', hib)
        res['higher_is_better'] = hib
        tests[metric] = res
        print(f"{metric:16s} Friedman chi2={res['stat']:8.2f} p={res['p']:.3e} "
              f"CD={res['cd']:.3f} N={res['n_blocks']}")
        order = np.argsort(res['mean_ranks'])
        print('   ranks: ' + '  '.join(
            f'{POLICY_ORDER[i]}={res["mean_ranks"][i]:.2f}' for i in order))

    fig_cd_diagram(tests['auc'],
                   'Critical-difference diagram - exploration efficiency (AUC), '
                   '60 paired trials', 'cd_auc.png')
    fig_cd_diagram(tests['distance_m'],
                   'Critical-difference diagram - distance to finish, '
                   '60 paired trials', 'cd_distance.png')
    fig_coverage_curves()
    fig_summary_bars(summary)

    out = os.path.join(HERE, 'results_analysis.json')
    json.dump({'summary': summary, 'tests': tests,
               'policy_order': POLICY_ORDER, 'tuned': data['tuned'],
               'n_blocks': tests['auc']['n_blocks']},
              open(out, 'w'), indent=2)
    print('\nWrote', out)
    print('Figures in', FIG)


if __name__ == '__main__':
    main()
