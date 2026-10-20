#!/usr/bin/env python3
"""Compare finished runs per arm: comparison.md (mean, sd, n and per-run values) + comparison.png
(key metrics, one dot per run) + comparison_trajectories.png (all trajectory figures tiled).

    compare.py DIR [DIR ...] [--out OUT_DIR]

DIRs are experiment folders (run sub-folders with summary.json) or single run folders. Runs with
the same 'arm' are pooled across DIRs, so a new arm can be compared with an older baseline.
"""
import glob
import json
import os
import sys

import numpy as np

# (label, path into summary.json, lower is better?)
METRICS = [
    ('final coverage %', ('final_coverage_pct',), False),
    ('minutes to stop', ('duration_s',), True),
    ('xte mean cm (all)', ('metrics', 'tracking_all', 'xte_mean'), True),
    ('heading dev mean deg', ('metrics', 'tracking_all', 'hdev_mean'), True),
    ('large deviation % (all)', ('metrics', 'tracking_all', 'large_dev_pct'), True),
    ('large deviation % (tunnel)', ('metrics', 'tracking_tunnel', 'large_dev_pct'), True),
    ('rotation events', ('metrics', 'rotation_events', 'count'), True),
    ('stall episodes', ('metrics', 'stall_episodes', 'count'), True),
    ('stuck % of time', ('metrics', 'stuck_pct'), True),
    ('turn on spot % of time', ('metrics', 'time_budget_pct', 'turn_on_spot'), True),
    ('reverse m', ('metrics', 'reverse_m'), None),
    ('distance m', ('metrics', 'distance_m'), True),
    ('goals reached', ('metrics', 'goals', 'reached'), False),
    ('goals given up', ('metrics', 'goals', 'gave_up'), True),
    ('no-progress cancels', ('metrics', 'goals', 'no_progress'), True),
    ('plans through unknown', ('metrics', 'plans', 'with_unknown_cells'), True),
]
SCALE = {'minutes to stop': 1 / 60, 'xte mean cm (all)': 100}
PLOT = ['final coverage %', 'minutes to stop', 'xte mean cm (all)', 'large deviation % (tunnel)',
        'rotation events', 'stuck % of time']


def get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def load(dirs):
    runs = []
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, '**', 'summary.json'), recursive=True)):
            s = json.load(open(f))
            if 'arm' not in s:        # a run folder made by sim_start: treat as its own arm
                s = {'arm': os.path.basename(os.path.dirname(f)), 'tag': os.path.basename(os.path.dirname(f)),
                     'metrics': s.get('whole_run', {}), 'duration_s': s.get('whole_run', {}).get('window_sim_s'),
                     'final_coverage_pct': (s.get('final_state', {}).get('coverage') or {}).get('pct'),
                     'stop_reason': 'manual'}
            s['_dir'] = os.path.dirname(f)
            runs.append(s)
    return runs


def compare(dirs, out=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    out = out or dirs[0]
    runs = load(dirs)
    arms = list(dict.fromkeys(r['arm'] for r in runs))
    L = ['# Comparison', '', f'Folders: {", ".join(dirs)}', '',
         '| metric | ' + ' | '.join(f'{a} (n={sum(r["arm"] == a for r in runs)})' for a in arms) + ' |',
         '|---|' + '---|' * len(arms)]
    vals = {}
    for label, path, _ in METRICS:
        row = []
        for a in arms:
            v = [get(r, path) for r in runs if r['arm'] == a]
            v = [x * SCALE.get(label, 1) for x in v if x is not None]
            vals[(label, a)] = v
            row.append('-' if not v else f'{np.mean(v):.2f} ± {np.std(v, ddof=1) if len(v) > 1 else 0:.2f}'
                       f'  ({", ".join(f"{x:.3g}" for x in v)})')
        L.append(f'| {label} | ' + ' | '.join(row) + ' |')
    L += ['', '## Runs', '', '| run | stop | minutes | coverage % |', '|---|---|---|---|']
    for r in runs:
        L.append(f'| {r["tag"]} | {r.get("stop_reason")} | {(r.get("duration_s") or 0) / 60:.1f} | '
                 f'{r.get("final_coverage_pct")} |')
    L += ['', 'Definitions: tools/rover_mcp/rosview.py docstring (same as validate.py). '
          'n < 3 per arm is a hint, not a confirmed result.']
    md = os.path.join(out, 'comparison.md')
    open(md, 'w').write('\n'.join(L) + '\n')

    fig, axs = plt.subplots(2, 3, figsize=(13, 7))
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    for ax, label in zip(axs.flat, PLOT):
        for i, a in enumerate(arms):
            v = vals.get((label, a), [])
            if v:
                ax.bar(i, np.mean(v), color=colors[i % len(colors)], alpha=0.55, width=0.6)
                ax.scatter(np.full(len(v), i) + np.linspace(-0.12, 0.12, len(v)), v, color='k', s=14, zorder=3)
        ax.set_xticks(range(len(arms)))
        ax.set_xticklabels(arms, rotation=20, fontsize=9)
        ax.set_title(label, fontsize=10)
        ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    png = os.path.join(out, 'comparison.png')
    fig.savefig(png, dpi=110)
    plt.close(fig)

    figs = [os.path.join(r['_dir'], 'trajectory.png') for r in runs
            if os.path.exists(os.path.join(r['_dir'], 'trajectory.png'))]
    if figs:
        ims = [Image.open(f).convert('RGB').resize((550, 550)) for f in figs]
        cols = min(len(arms), 4) or 1
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new('RGB', (550 * cols, 550 * rows), 'white')
        for k, im in enumerate(ims):
            sheet.paste(im, ((k % cols) * 550, (k // cols) * 550))
        sheet.save(os.path.join(out, 'comparison_trajectories.png'))
    return md, png


if __name__ == '__main__':
    a = sys.argv[1:]
    o = None
    if '--out' in a:
        i = a.index('--out')
        o = a[i + 1]
        a = a[:i] + a[i + 2:]
    md, png = compare(a, o)
    print(open(md).read())
    print('figure:', png)
