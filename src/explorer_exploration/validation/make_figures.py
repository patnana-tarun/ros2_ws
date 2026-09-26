"""Generate all figures and capture the paper-reproduction table."""

import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'kinematic_sim'))
import tad_kinematic_sim as sim  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, 'figures')
os.makedirs(FIG, exist_ok=True)

INK = '#1a1a2e'
ACCENT = '#2d6a9f'
WARN = '#c1666b'
GOOD = '#4a7c59'
GREY = '#8a8a99'

plt.rcParams.update({
    'font.size': 9, 'axes.edgecolor': INK, 'axes.labelcolor': INK,
    'text.color': INK, 'xtick.color': INK, 'ytick.color': INK,
    'axes.spines.top': False, 'axes.spines.right': False,
    'figure.dpi': 200, 'savefig.dpi': 200,
})

core = json.load(open(os.path.join(HERE, 'results_core.json')))
beh = json.load(open(os.path.join(HERE, 'results_behavioral.json')))


# --------------------------------------------------------------------------
def fig_ablation():
    st = beh['V5_V7']['stats']
    comps = beh['V5_V7']['comparisons']
    base = beh['V5_V7']['baseline_label']
    labels = list(st.keys())
    short = [l.split('(')[0].strip() + '\n(' + l.split('(')[1] for l in labels]

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.8))
    for ax, metric, title, unit in (
            (axes[0], 'coverage_pct', 'Map coverage achieved', '%'),
            (axes[1], 'path_distance_m', 'Path distance travelled', 'm')):
        means = [st[l][metric]['mean'] for l in labels]
        los = [st[l][metric]['mean'] - st[l][metric]['ci95'][0] for l in labels]
        his = [st[l][metric]['ci95'][1] - st[l][metric]['mean'] for l in labels]
        colors = [ACCENT if l == base else GREY for l in labels]
        x = np.arange(len(labels))
        ax.bar(x, means, yerr=[los, his], capsize=3, color=colors,
               edgecolor=INK, linewidth=0.6, width=0.64,
               error_kw=dict(ecolor=INK, lw=0.9))
        ax.set_xticks(x)
        ax.set_xticklabels(short, fontsize=7)
        ax.set_ylabel(f'{title} ({unit})', fontsize=8.5)
        ax.set_title(f'{title}  -  mean +/- 95% CI, n={st[labels[0]][metric]["n"]} seeds',
                     fontsize=9, color=INK)
        # significance annotation vs baseline
        for i, l in enumerate(labels):
            if l == base:
                continue
            p = comps[l][metric]['p_value']
            mark = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'n.s.'
            ax.annotate(mark, (i, means[i] + his[i]), ha='center', va='bottom',
                        fontsize=7, color=WARN if mark != 'n.s.' else GREY)
    fig.suptitle('V5/V7  Ablation of the TAD terms (paired, identical maps per seed)',
                 fontsize=10, y=1.0)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'ablation.png'), bbox_inches='tight')
    plt.close(fig)


# --------------------------------------------------------------------------
def fig_complexity():
    pts = core['V8']['points']
    N = np.array([p['cells'] for p in pts], float)
    T = np.array([p['seconds'] for p in pts], float) * 1000.0
    slope = core['V8']['loglog_slope']
    r2 = core['V8']['r_squared']

    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    ax.loglog(N, T, 'o-', color=ACCENT, lw=1.4, ms=5, label='measured')
    ref = T[0] * (N / N[0]) ** 1.0
    ax.loglog(N, ref, '--', color=GOOD, lw=1.2, label='ideal linear  O(N)')
    ref2 = T[0] * (N / N[0]) ** 2.0
    ax.loglog(N, ref2, ':', color=WARN, lw=1.2, label='quadratic  O(N$^2$)')
    ax.set_xlabel('grid cells N')
    ax.set_ylabel('process_map latency (ms)')
    ax.set_title(f'V8  Empirical scaling: exponent {slope:.3f} (R$^2$={r2:.4f})',
                 fontsize=9)
    ax.legend(fontsize=7.5, frameon=False)
    ax.grid(True, which='both', alpha=0.15)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'complexity.png'), bbox_inches='tight')
    plt.close(fig)


# --------------------------------------------------------------------------
def fig_hotspot():
    fig, ax = plt.subplots(figsize=(5.4, 2.6))
    fig.set_size_inches(5.8, 2.9)
    names = ['per-cluster scan\n4-conn, K=9851\n(pre-fix)',
             'per-cluster scan\n8-conn, K=241\n(current)',
             'single-pass\nargsort/bincount']
    vals = [1428.9, 35.1, 1.4]
    bars = ax.barh(names, vals, color=[WARN, ACCENT, GOOD], edgecolor=INK,
                   linewidth=0.6, height=0.5)
    ax.set_xscale('log')
    ax.set_xlabel('time to group all frontier clusters, 260x260 grid (ms, log scale)')
    for b, v in zip(bars, vals):
        ax.text(v * 1.15, b.get_y() + b.get_height() / 2, f'{v:.1f} ms',
                va='center', fontsize=8, color=INK)
    ax.tick_params(axis='y', labelsize=7)
    ax.set_title('V8  Hot spot: the connectivity fix removed 41x of it',
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'hotspot.png'), bbox_inches='tight')
    plt.close(fig)


# --------------------------------------------------------------------------
def fig_divergence():
    v6 = beh['V6']
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 2.9))
    ax = axes[0]
    same = v6['decision_points'] - v6['divergent_decisions']
    ax.barh(['TAD == nearest', 'TAD != nearest'], [same, v6['divergent_decisions']],
            color=[GREY, ACCENT], edgecolor=INK, linewidth=0.6, height=0.5)
    ax.set_xlabel('decision points (n=%d)' % v6['decision_points'])
    ax.set_title('V6  TAD vs nearest-frontier: %.1f%% divergence'
                 % (v6['divergence_rate'] * 100), fontsize=9)
    for i, val in enumerate([same, v6['divergent_decisions']]):
        ax.text(val + 6, i, str(val), va='center', fontsize=8)

    ax = axes[1]
    ax.bar(['mean', 'median'],
           [v6['tad_to_nearest_distance_ratio_mean'],
            v6['tad_to_nearest_distance_ratio_median']],
           color=ACCENT, edgecolor=INK, linewidth=0.6, width=0.45)
    ax.axhline(1.0, color=WARN, ls='--', lw=1.0)
    ax.text(1.45, 1.08, 'nearest-frontier = 1.0x', fontsize=7, color=WARN, ha='right')
    ax.set_ylabel('chosen distance / nearest distance')
    ax.set_title('TAD deliberately forgoes the closest frontier', fontsize=9)
    for i, v in enumerate([v6['tad_to_nearest_distance_ratio_mean'],
                           v6['tad_to_nearest_distance_ratio_median']]):
        ax.text(i, v + 0.15, f'{v:.2f}x', ha='center', fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'divergence.png'), bbox_inches='tight')
    plt.close(fig)


# --------------------------------------------------------------------------
def capture_reproduction():
    """Run the paper-reproduction environments once, for context only."""
    rows = []
    for name, w, h, rx, ry, cyc, sx, sy in sim.ENVIRONMENTS:
        r = sim.run_environment(name, w, h, rx, ry, cyc, sx, sy)
        p = sim.PAPER_RESULTS[name]
        rows.append({
            'env': name,
            'time_s': r['exploration_time_s'], 'paper_time_s': p['time'],
            'distance_m': r['path_distance_m'], 'paper_distance_m': p['distance'],
            'turns': r['turning_points'], 'paper_turns': p['turns'],
            'goals': r['goal_count'], 'coverage_pct': r['coverage_pct'],
            'completed': r['completed'], 'stalled': r['stalled'],
        })
        print(f"  {name}: t={r['exploration_time_s']:.1f}s (paper {p['time']}s), "
              f"d={r['path_distance_m']:.2f}m (paper {p['distance']}m), "
              f"cov={r['coverage_pct']:.1f}%")
    json.dump(rows, open(os.path.join(HERE, 'results_reproduction.json'), 'w'), indent=2,
              default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o))
    return rows


if __name__ == '__main__':
    print('Capturing paper-reproduction table...')
    capture_reproduction()
    print('Rendering figures...')
    fig_ablation()
    fig_complexity()
    fig_hotspot()
    fig_divergence()
    print('Figures written to', FIG)
    for f in sorted(os.listdir(FIG)):
        print('  ', f)
