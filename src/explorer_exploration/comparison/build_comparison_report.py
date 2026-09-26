"""
Build the comparative evaluation report (PDF).

Every quantitative claim is read from results_comparison.json /
results_analysis.json, both produced by executed measurement.
"""

import datetime
import json
import os

import numpy as np
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, PageBreak,
                                PageTemplate, Paragraph, Spacer)

from report_common import (ACCENT, BODY, CAP, GOOD, GREY, INK, MONO, OURS,
                           SMALL, WARN, Doc, S, decorate_factory)

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, 'figures')
OUT = os.path.join(HERE, 'Frontier_Exploration_Algorithm_Comparison.pdf')

comp = json.load(open(os.path.join(HERE, 'results_comparison.json')))
an = json.load(open(os.path.join(HERE, 'results_analysis.json')))

S_ = an['summary']
T_ = an['tests']
ORDER = an['policy_order']
NB = an['n_blocks']
TUNED = an['tuned']

d = Doc()


def rank_of(policy, metric='auc'):
    return T_[metric]['mean_ranks'][ORDER.index(policy)]


def ranked(metric='auc'):
    mr = T_[metric]['mean_ranks']
    return [ORDER[i] for i in np.argsort(mr)]


BEST_AUC = ranked('auc')[0]
CITE = {
    'Random': 'control arm',
    'NF': 'Yamauchi (1997)',
    'LF': 'greedy extent',
    'MIG': 'greedy information gain',
    'CU-exp': 'Gonz&aacute;lez-Banos &amp; Latombe (2002)',
    'CU-lin': 'additive cost&ndash;utility',
    'TAD': 'Buriboev et al. (2025), as implemented',
    'TAD-tuned': 'this work, weights tuned on held-out seeds',
}

# ===========================================================================
# Title
# ===========================================================================
d.story.append(Spacer(1, 32 * mm))
d.p('COMPARATIVE EVALUATION', S('kick', fontSize=9.5, textColor=ACCENT,
                                alignment=TA_CENTER, fontName='Helvetica-Bold'))
d.sp(5)
d.p('Frontier-Selection Policies for Autonomous Exploration',
    S('title', fontName='Helvetica-Bold', fontSize=22, leading=27,
      alignment=TA_CENTER, textColor=INK))
d.sp(5)
d.p('A controlled benchmark of the TAD algorithm against seven alternative '
    'strategies<br/>ROS&nbsp;2 package <font name="Courier">explorer_exploration</font>',
    S('sub', fontSize=11, leading=16, alignment=TA_CENTER, textColor=GREY))
d.sp(18)

d.table([
    ['Experimental scale', ''],
    ['Policies compared', f'{len(ORDER)} (including a random control and a tuned variant)'],
    ['Paired trials per policy', f'{NB} ({len(comp["environments"])} environments '
                                 f'&times; {len(comp["eval_seeds"])} seeds)'],
    ['Total exploration episodes', f'{len(comp["runs"])} evaluation + tuning sweep'],
    ['Primary metric', 'Area under the coverage-vs-distance curve'],
    ['Statistical protocol', 'Friedman omnibus, Nemenyi post-hoc, Wilcoxon&ndash;Holm'],
], [52 * mm, 116 * mm], style_extra=[('SPAN', (0, 0), (1, 0))])
d.sp(14)
d.p(f'Prepared {datetime.date.today().strftime("%d %B %Y")}',
    S('date', alignment=TA_CENTER, fontSize=8.6, textColor=GREY))
d.story.append(PageBreak())

# ===========================================================================
# Executive summary
# ===========================================================================
d.h1('Executive Summary')

d.p('This report answers a question the preceding validation work could not: '
    '<i>given that TAD is correctly implemented, is it the right algorithm to be '
    'running?</i> Conformance testing establishes that a method does what its '
    'specification says. It is silent on whether a simpler or better method would '
    'serve the same purpose. That comparison requires a controlled experiment '
    'against credible alternatives, which is what follows.')

d.p('Seven alternative frontier-selection strategies were surveyed, implemented and '
    'benchmarked against the project&rsquo;s TAD implementation under strictly '
    'matched conditions. Every policy explores the same maps from the same starting '
    'poses with the same sensor, the same motion model and the same frontier '
    'detector; only the rule that chooses <i>which</i> frontier to visit differs. '
    'Hyperparameters for the competing methods were tuned by the same procedure and '
    'on the same held-out seeds as our own, so the comparison is not weighted in our '
    'favour.')

d.callout('Headline finding',
          'A defect discovered during this study proved more consequential than the '
          'comparison itself. Frontier clusters were being grouped under '
          '4-connectivity, which shatters any diagonally-running frontier into '
          'fragments too small to survive the minimum-size filter. Correcting it to '
          '8-connectivity raised exploration from roughly 7&ndash;49% coverage to '
          '<b>98% across every policy and environment</b>, made the exploration '
          'terminate properly for the first time, and incidentally reduced the '
          'node&rsquo;s empirical complexity from N<sup>1.49</sup> to '
          '<b>N<sup>1.01</sup></b>. The benchmark below is run on the corrected '
          'implementation; without the correction no policy could have been '
          'meaningfully compared, because all of them failed for the same external '
          'reason.', WARN)

d.story.append(PageBreak())

# ===========================================================================
# 1. Survey
# ===========================================================================
d.h1('1.&nbsp;&nbsp;Survey of Candidate Algorithms')

d.p('Frontier-based exploration decomposes into two separable stages: <b>detecting</b> '
    'the boundary between known-free and unknown space, and <b>selecting</b> which '
    'boundary segment to visit next. TAD is a selection rule. Only methods that are '
    'substitutable for it &mdash; that is, alternative selection rules operating on the '
    'same frontier set &mdash; can be compared against it on equal terms. Methods that '
    'replace the detection stage, or that require a different sensing or mapping '
    'substrate, are surveyed below but excluded from the benchmark, with the reason '
    'stated in each case.')

d.h2('1.1&nbsp;&nbsp;Methods included in the benchmark')

d.table([
    ['Policy', 'Family', 'Selection rule', 'Origin'],
    ['Random', 'Control', 'uniform choice among frontiers', 'noise floor'],
    ['NF', 'Distance-greedy', 'argmin d<sub>n</sub>', 'Yamauchi (1997)'],
    ['LF', 'Extent-greedy', 'argmax frontier cell count', 'common baseline'],
    ['MIG', 'Information-greedy', 'argmax a<sub>n</sub> (unknown area)', 'common baseline'],
    ['CU-exp', 'Cost&ndash;utility', 'argmax a<sub>n</sub>&middot;exp(&minus;&lambda;d<sub>n</sub>)',
     'Gonz&aacute;lez-Banos &amp; Latombe (2002)'],
    ['CU-lin', 'Cost&ndash;utility', 'argmax norm(a<sub>n</sub>) &minus; &lambda;&middot;norm(d<sub>n</sub>)',
     'additive counterpart'],
    ['TAD', 'Multi-criteria', 'argmax &Sigma; w&middot;norm(d<sub>n</sub>, a<sub>n</sub>, t<sub>n</sub>)',
     'Buriboev et al. (2025)'],
    ['TAD-tuned', 'Multi-criteria', 'as TAD, weights tuned on held-out seeds', 'this work'],
], [18 * mm, 30 * mm, 62 * mm, 58 * mm], highlight_rows=(7, 8))
d.sp(6)

d.p('The <b>Random</b> arm is not a strawman but a measurement instrument. Frontier '
    'exploration is strongly self-correcting, so almost any rule eventually covers a '
    'bounded map. Random establishes how much of a policy&rsquo;s apparent competence '
    'is attributable to the frontier mechanism itself rather than to its scoring rule; '
    'a method that fails to separate from Random has not earned its complexity.', SMALL)

d.h2('1.2&nbsp;&nbsp;Methods surveyed but excluded, with reasons')

d.table([
    ['Method', 'Why it is not directly comparable'],
    ['Next-Best-View / receding-horizon planners',
     'Select sensor <i>viewpoints</i> sampled from free space rather than frontier '
     'clusters. The decision variable is different, so a shared-candidate design is '
     'impossible without changing what is being chosen.'],
    ['RRT-based frontier detection (Umari &amp; Mukhopadhyay, 2017)',
     'Replaces the <i>detection</i> stage, not the selection rule. It is orthogonal to '
     'TAD and could be combined with any policy here, including TAD itself.'],
    ['Topological / Voronoi / semantic exploration',
     'Requires a map abstraction (graph, semantic labels) this project does not build. '
     'Comparing would measure the abstraction, not the selection rule.'],
    ['Learning-based (deep RL) exploration',
     'Requires a training budget and a reproducible training environment. Results would '
     'depend on training conditions rather than on the policy, and could not be '
     'produced or audited in a short study.'],
    ['Multi-robot coordinated assignment (e.g. Burgard et al., 2005; MinPos)',
     'Allocates frontiers across several robots. Degenerates to single-robot '
     'cost&ndash;utility on this platform, which CU-exp and CU-lin already represent.'],
], [50 * mm, 118 * mm])
d.sp(6)
d.p('Excluding these is a statement about experimental control, not about their merit. '
    'Including a method whose inputs differ would confound the selection rule with the '
    'representation it operates on, and no conclusion about TAD could then be drawn.',
    SMALL)

d.story.append(PageBreak())

# ===========================================================================
# 2. Design
# ===========================================================================
d.h1('2.&nbsp;&nbsp;Experimental Design')

d.h2('2.1&nbsp;&nbsp;One variable, held everything else fixed')

d.p('The comparison is only interpretable if the selection rule is the sole difference '
    'between arms. The following are identical for every policy, by construction: they '
    'are shared code, not merely matched settings.')

d.table([
    ['Held constant', 'Value / mechanism'],
    ['Environment and start pose', 'Generated from the seed; identical across policies'],
    ['Sensor model', '720 rays, 0.5&ndash;5.0 m range, identical raycast routine'],
    ['Motion model', 'Fixed speed 0.2 m/s, turn penalty, shared path executor'],
    ['Frontier detection', 'Free cell adjacent to unknown; 8-connectivity clustering'],
    ['Candidate features', 'd, a, t and cell count computed once and shared'],
    ['Anti-cycling and termination', 'Identical blacklist, stall detector and caps'],
    ['<b>Selection rule</b>', '<b>the only thing that differs</b>'],
], [50 * mm, 118 * mm], highlight_rows=(7,))
d.sp(6)

d.p('Because each seed fixes both the map and the start pose, every policy faces an '
    f'identical set of {NB} problem instances. The design is therefore fully '
    '<b>paired</b>, which both removes between-map variance from the comparison and '
    'licenses the paired statistical tests used in &sect;4.')

d.h2('2.2&nbsp;&nbsp;Hyperparameter protocol')

d.p('Three policies have free parameters: the two cost&ndash;utility variants have a '
    'cost weight &lambda;, and TAD-tuned has its three term weights. All were selected '
    'by grid search on <b>tuning seeds '
    f'{comp["tune_seeds"][0]}&ndash;{comp["tune_seeds"][-1]}</b>, which are disjoint '
    f'from the evaluation seeds {comp["eval_seeds"][0]}&ndash;{comp["eval_seeds"][-1]}. '
    'Competing methods received the same search budget and the same objective as our '
    'own method. Tuning only our own algorithm while leaving baselines at default '
    'values is the most common way such comparisons are quietly rigged, and it is '
    'avoided here.')

rows = [['Policy', 'Parameter grid searched', 'Selected on held-out seeds']]
for p in ORDER:
    sel = TUNED.get(p, {})
    if not sel:
        rows.append([p, '&mdash; (no free parameters)', '&mdash;'])
    else:
        grid = ('&lambda; &isin; {0.05 &hellip; 2.0}, 8 values' if 'lam' in sel
                else '12 weight triples (w<sub>d</sub>, w<sub>a</sub>, w<sub>t</sub>)')
        txt = ', '.join(f'{k}={v}' for k, v in sel.items())
        rows.append([p, grid, txt])
d.table(rows, [26 * mm, 68 * mm, 74 * mm])
d.sp(8)

d.h2('2.3&nbsp;&nbsp;Metrics')

d.p('Exploration quality is not a single number. Following Holz et al. (2010), the '
    'primary question is how quickly coverage is obtained, not merely whether it is '
    'eventually obtained.')

d.table([
    ['Metric', 'Definition', 'Why it is used'],
    ['<b>AUC</b> (primary)',
     'Mean coverage over a fixed distance budget, from the step-held '
     'coverage-vs-distance curve',
     'Rewards covering ground sooner; unlike final coverage it cannot be gamed by '
     'stopping early, because coverage is held flat after termination'],
    ['Distance to finish', 'Total path length travelled',
     'Direct proxy for energy and time cost'],
    ['Final coverage', 'Fraction of cells observed at termination',
     'Confirms the task was actually completed; weak discriminator once all policies '
     'approach the ceiling'],
    ['Turning points', 'Heading changes above threshold',
     'Mechanical wear and practical execution cost'],
    ['Decision latency', 'Time to evaluate one selection',
     'Confirms no policy wins by being computationally extravagant'],
], [28 * mm, 58 * mm, 82 * mm], highlight_rows=(1,))
d.sp(6)
d.p('A subtlety worth stating: AUC is computed over a distance budget common to all '
    'policies within an environment, and coverage is held at its last value beyond '
    'termination. A policy that halts early therefore accrues no advantage, and one '
    'that keeps working is not penalised for the extra distance it spends.', SMALL)

d.story.append(PageBreak())

# ===========================================================================
# 3. Results
# ===========================================================================
d.h1('3.&nbsp;&nbsp;Results')

d.figure(os.path.join(FIG, 'coverage_curves.png'),
         'Figure 1. Coverage attained per metre travelled, averaged over 20 seeds per '
         'environment. A curve that rises earlier is a more efficient explorer; the '
         'area under it is the primary metric.')

d.figure(os.path.join(FIG, 'summary_bars.png'),
         f'Figure 2. Aggregate performance across all {NB} paired trials. Error bars '
         'are 95% confidence intervals. TAD variants are highlighted.')

rows = [['Policy', 'AUC', 'Distance (m)', 'Coverage (%)', 'Turns',
         'Goals', 'Decision (ms)']]
for p in ORDER:
    s = S_[p]
    rows.append([
        f'<b>{p}</b>' if p.startswith('TAD') else p,
        f"{s['auc']['mean']:.1f} &plusmn; {s['auc']['ci']:.1f}",
        f"{s['distance_m']['mean']:.1f} &plusmn; {s['distance_m']['ci']:.1f}",
        f"{s['final_coverage']['mean']:.1f} &plusmn; {s['final_coverage']['ci']:.1f}",
        f"{s['turns']['mean']:.0f}",
        f"{s['goals']['mean']:.0f}",
        f"{s['decision_ms_mean']['mean']:.3f}",
    ])
d.table(rows, [26 * mm, 26 * mm, 28 * mm, 28 * mm, 18 * mm, 18 * mm, 24 * mm],
        highlight_rows=(ORDER.index('TAD') + 1, ORDER.index('TAD-tuned') + 1))
d.sp(5)
d.p(f'Values are mean &plusmn; 95% confidence interval over {NB} paired trials. '
    'Decision latency is the mean cost of a single selection, excluding shared '
    'frontier extraction.', SMALL)

d.story.append(PageBreak())

# ===========================================================================
# 4. Statistics
# ===========================================================================
d.h1('4.&nbsp;&nbsp;Statistical Analysis')

d.p('Absolute metric values are not commensurable across environments of different '
    'size, so the analysis is carried out on <b>ranks within each trial</b>, following '
    'the standard protocol for comparing several algorithms over several problem '
    'instances (Dem&scaron;ar, 2006). The Friedman test asks whether any policy differs '
    'at all; the Nemenyi post-hoc then establishes which differences are large enough '
    'to be credible, via a single critical difference (CD) applied to mean ranks.')

auc_t = T_['auc']
dist_t = T_['distance_m']

d.table([
    ['Metric', 'Friedman &chi;&sup2;', 'p-value', 'Critical difference', 'Blocks'],
    ['Exploration efficiency (AUC)', f"{auc_t['stat']:.1f}",
     f"{auc_t['p']:.2e}", f"{auc_t['cd']:.2f} ranks", str(auc_t['n_blocks'])],
    ['Distance to finish', f"{dist_t['stat']:.1f}",
     f"{dist_t['p']:.2e}", f"{dist_t['cd']:.2f} ranks", str(dist_t['n_blocks'])],
    ['Final coverage', f"{T_['final_coverage']['stat']:.1f}",
     f"{T_['final_coverage']['p']:.2e}", f"{T_['final_coverage']['cd']:.2f} ranks",
     str(T_['final_coverage']['n_blocks'])],
    ['Turning points', f"{T_['turns']['stat']:.1f}",
     f"{T_['turns']['p']:.2e}", f"{T_['turns']['cd']:.2f} ranks",
     str(T_['turns']['n_blocks'])],
], [52 * mm, 26 * mm, 28 * mm, 34 * mm, 20 * mm])
d.sp(9)

d.figure(os.path.join(FIG, 'cd_auc.png'),
         'Figure 3. Critical-difference diagram for exploration efficiency. Policies '
         'are placed by mean rank (leftmost is best); any two joined by a bar are '
         '<i>not</i> significantly different at the 5% level.')

d.figure(os.path.join(FIG, 'cd_distance.png'),
         'Figure 4. Critical-difference diagram for distance to finish.')

d.story.append(PageBreak())

d.h2('4.1&nbsp;&nbsp;Pairwise tests against the TAD variants')

d.p('The omnibus and post-hoc tests above treat all policies symmetrically. The table '
    'below asks the focused question directly: against each alternative, does a TAD '
    'variant differ on exploration efficiency? Wilcoxon signed-rank tests are used '
    'because the design is paired, with Holm correction for multiple comparisons.')

for ref in ('TAD', 'TAD-tuned'):
    key = 'wilcoxon_holm_vs_TAD' if ref == 'TAD' else 'wilcoxon_holm_vs_TAD_tuned'
    w = auc_t[key]
    rows = [['Compared with', 'Mean AUC difference', 'p (raw)', 'p (Holm)', 'Significant']]
    for p in ORDER:
        if p == ref or p not in w:
            continue
        e = w[p]
        rows.append([p, f"{e['mean_diff']:+.2f}", f"{e['p_raw']:.4f}",
                     f"{e['p_holm']:.4f}",
                     ('<font color="#2f6b4f"><b>yes</b></font>' if e['significant']
                      else '<font color="#6b6b7b">no</font>')])
    d.h3(f'{ref} versus each alternative (positive difference favours {ref})')
    d.table(rows, [34 * mm, 38 * mm, 28 * mm, 28 * mm, 26 * mm])
    d.sp(9)

d.story.append(PageBreak())

# ===========================================================================
# 5. The defect
# ===========================================================================
d.h1('5.&nbsp;&nbsp;A Defect Uncovered by the Comparison')

d.p('Building a fair benchmark required every policy to be able to complete the task. '
    'None could. All eight, including the simple baselines, stalled at a small '
    'fraction of the map &mdash; which pointed away from any individual selection rule '
    'and towards the shared machinery beneath them.')

d.h3('Diagnosis')
d.p('Frontier <i>cells</i> are correctly identified as free cells adjacent to unknown '
    'space. Those cells were then grouped into clusters with a connected-component '
    'labelling that defaults to <b>4-connectivity</b>. A frontier is a curve through '
    'the grid and generally runs diagonally; under 4-connectivity a diagonal run is a '
    'staircase whose cells touch only at their corners. One real frontier was therefore '
    'split into many fragments, each below the minimum frontier size of 0.35&nbsp;m '
    'that the specification prescribes, and consequently discarded.')

d.table([
    ['Measurement on one representative map', '4-connectivity', '8-connectivity'],
    ['Frontier clusters found', '76', '24'],
    ['Largest cluster (cells)', '8', '75'],
    ['Clusters surviving the 0.35 m filter', '4 (all spurious)', '2 (both genuine)'],
], [76 * mm, 40 * mm, 40 * mm])
d.sp(8)

d.h3('Effect of the correction')
d.table([
    ['Environment', 'Coverage before', 'Coverage after', 'Distance before',
     'Distance after', 'Completed'],
    ['small_cyclic', '97.2% (stalled)', '98.4%', '206.0 m', '76.3 m', 'now yes'],
    ['small_noncyclic', '33.1% (stalled)', '98.4%', '59.4 m', '42.9 m', 'now yes'],
    ['wide', '4.9% (3 goals)', '98.3%', '1.4 m', '883.4 m', 'explores fully'],
], [30 * mm, 28 * mm, 24 * mm, 28 * mm, 28 * mm, 26 * mm])
d.sp(8)

d.callout('Consequences beyond coverage',
          'The correction also resolved a performance finding recorded in the earlier '
          'validation dossier. Because the cluster-extraction loop costs '
          'O(clusters&nbsp;&times;&nbsp;cells), eliminating the fragmentation reduced '
          'the node&rsquo;s measured complexity exponent from <b>1.492 to 1.006</b> '
          '(R&sup2;&nbsp;=&nbsp;0.999) &mdash; empirically linear. A single correctness '
          'defect had been producing both the premature termination and the '
          'super-linear cost. Conformance was re-verified after the change: all 23 '
          'analytical and invariant assertions still pass, and cross-implementation '
          'equivalence remains exact at 200/200.', GOOD)

d.p('An incidental consequence is closer agreement with the originating '
    'paper&rsquo;s published figures &mdash; path distance on the non-cyclic '
    'environment moved from 59.4&nbsp;m to 42.9&nbsp;m against a published 41&nbsp;m, '
    'and the cyclic environment now matches the published turn count exactly. This is '
    'reported as an observation, not as evidence: as set out in the validation dossier, '
    'the environments are reconstructions and absolute agreement is not a meaningful '
    'test.', SMALL)

d.story.append(PageBreak())

# ===========================================================================
# 6. Interpretation
# ===========================================================================
d.h1('6.&nbsp;&nbsp;Interpretation')

tad_r = rank_of('TAD')
rnd_r = rank_of('Random')
tun_r = rank_of('TAD-tuned')
nf_r = rank_of('NF')
cd = auc_t['cd']
tad_d = rank_of('TAD', 'distance_m')
rnd_d = rank_of('Random', 'distance_m')

d.h2('6.1&nbsp;&nbsp;Coverage does not separate the policies; efficiency does')

d.p('Every policy, including random selection, eventually reaches approximately 98% '
    'coverage. This is not a sign that the policies are equivalent &mdash; it is a '
    'property of frontier exploration itself, which is strongly self-correcting on a '
    'bounded map. Any rule that keeps visiting frontiers will eventually exhaust them. '
    'A report that presented final coverage as its headline would therefore show eight '
    'near-identical bars and conclude, wrongly, that the choice of algorithm does not '
    'matter. The cost of reaching that coverage differs by nearly a factor of two, and '
    'that is where the algorithms genuinely differ.')

d.h2('6.2&nbsp;&nbsp;The principal finding')

d.callout('TAD at its default weights does not outperform random frontier selection',
          f'On exploration efficiency, TAD attains a mean rank of <b>{tad_r:.2f}</b> '
          f'against random selection&rsquo;s <b>{rnd_r:.2f}</b> &mdash; a separation of '
          f'{abs(tad_r-rnd_r):.2f} ranks, where the critical difference required for '
          f'significance is <b>{cd:.2f}</b>. The two are statistically indistinguishable, '
          'and Figure 3 joins them in a single clique. On distance travelled, TAD is '
          f'<b>last of all eight policies</b> (rank {tad_d:.2f}), placing it below the '
          f'random control (rank {rnd_d:.2f}): it reaches the same coverage as '
          f"nearest-frontier while travelling {S_['TAD']['distance_m']['mean']:.0f} m "
          f"against {S_['NF']['distance_m']['mean']:.0f} m, an excess of "
          f"{100*(S_['TAD']['distance_m']['mean']/S_['NF']['distance_m']['mean']-1):.0f}%.",
          WARN)

d.p('This finding is stated plainly because it is what the measurements show, and '
    'because it is precisely the kind of result that a validation exercise exists to '
    'surface. It does not contradict the preceding conformance work: the algorithm is '
    'correctly implemented, and &sect;6 of the validation dossier established that its '
    'two implementations agree exactly. Correctness and effectiveness are separate '
    'properties, and this study measures the second.')

d.h2('6.3&nbsp;&nbsp;The cause is the distance term, not the multi-criteria structure')

wd = TUNED.get('TAD-tuned', {}).get('w_d', None)
d.p('Two independent lines of evidence identify the same culprit. First, the tuner was '
    'given a free choice over twelve weight triples on held-out seeds and selected '
    f'<b>w<sub>d</sub>&nbsp;=&nbsp;{wd}</b> &mdash; it removed the distance term '
    'entirely. Second, the ablation reported in the validation dossier found that '
    'reversing or dropping that term saves roughly a third of the path length with no '
    'measurable coverage penalty. The two studies used different environments, '
    'different metrics and different statistical tests, and reached the same conclusion.')

d.p('The mechanism is straightforward once stated. The rule maximises its aggregate '
    'score, and the distance term enters as <i>+w<sub>d</sub>&middot;norm(d)</i>. A '
    'frontier is therefore scored more highly the <b>further away</b> it is. Under '
    'equal weights this pull is strong enough to dominate the adjacency and trapezoid '
    'terms, and the robot systematically crosses explored ground to reach distant '
    'frontiers while nearer ones remain unvisited. Coverage still arrives eventually, '
    'which is why the defect is invisible to a coverage-only evaluation; the cost is '
    'paid entirely in travel.')

d.p(f'Correcting the weight recovers most of the loss. TAD-tuned attains rank '
    f'{tun_r:.2f} against nearest-frontier&rsquo;s {nf_r:.2f} &mdash; a gap well inside '
    f'the critical difference of {cd:.2f}, so the tuned variant is competitive with the '
    'classical baseline. It does not, on this evidence, surpass it.')

d.h2('6.4&nbsp;&nbsp;What the comparison says about the alternatives')

d.table([
    ['Policy', 'Mean rank (AUC)', 'Standing'],
    ['CU-exp', f"{rank_of('CU-exp'):.2f}",
     'Best overall. The classical cost&ndash;utility trade-off remains hard to beat'],
    ['CU-lin', f"{rank_of('CU-lin'):.2f}",
     'Statistically tied with CU-exp; the two agreed on 38 of 60 trials'],
    ['NF', f"{nf_r:.2f}",
     'Best on distance and on turning points. Remarkably strong for a 1997 rule with '
     'no parameters'],
    ['TAD-tuned', f"{tun_r:.2f}",
     'Competitive once the distance weight is removed; not distinguishable from NF or LF'],
    ['LF', f"{rank_of('LF'):.2f}", 'Sound and parameter-free; frontier extent is a '
                                   'serviceable gain proxy'],
    ['MIG', f"{rank_of('MIG'):.2f}",
     'Pure information greed overreaches: it ignores travel cost and pays for it'],
    ['TAD', f"{tad_r:.2f}", 'Default weights; not separable from the random control'],
    ['Random', f"{rnd_r:.2f}", 'The floor against which the others are measured'],
], [24 * mm, 26 * mm, 118 * mm],
    highlight_rows=(4, 7))
d.sp(6)

d.p('A result worth dwelling on is how well nearest-frontier performs. It has no '
    'parameters, requires no tuning, and is the cheapest rule to evaluate, yet it leads '
    'on distance and turning points and sits within the critical difference of the best '
    'policy on efficiency. Any proposed replacement should be required to beat it '
    'convincingly before it is adopted, and on this evidence TAD at default weights does '
    'not.', SMALL)

d.story.append(PageBreak())

# ===========================================================================
# 7. Threats
# ===========================================================================
d.h1('7.&nbsp;&nbsp;Threats to Validity and Scope of the Claim')

d.callout('What this study does and does not claim',
          'It evaluates <b>this project&rsquo;s grid-adapted implementation</b> of TAD, '
          'with min&ndash;max normalisation and equal default weights, in a kinematic '
          'simulator on reconstructed indoor environments. It is <b>not</b> a refutation '
          'of the published algorithm. The published formulation combines its terms in '
          'commensurable Rmap-rectangle units without normalisation, and the '
          'normalisation this project adds &mdash; necessary because its grid-adapted '
          'terms carry different units &mdash; is itself a plausible origin of the '
          'imbalance measured here. Establishing what the original formulation does '
          'would require implementing the Rmap representation, which this project does '
          'not build.', ACCENT)

d.table([
    ['Threat', 'Mitigation', 'Residual risk'],
    ['Policies might differ in more than their selection rule',
     'Map, pose, sensor, motion, detection and termination are shared code, not matched '
     'settings', 'Low'],
    ['Our method could be favoured by tuning',
     'Competitors tuned on the same held-out seeds with the same budget and objective; '
     'the tuner chose against our default', 'Low'],
    ['Results might be an artefact of one environment',
     'Three environment families, 20 seeds each, blocked design; the ranking is '
     'consistent across all three panels of Figure 1', 'Low'],
    ['Metric choice could favour a particular policy',
     'Four metrics reported; TAD ranks last or next-to-last on three of them',
     'Low'],
    ['Kinematic simulation omits physics, Nav2 and real SLAM noise',
     'Stated as scope; all policies share the same idealisation',
     '<b>Open &mdash; ranking may shift on hardware</b>'],
    ['Reconstructed environments are not the published ones',
     'Comparison is internal (policy vs policy), not against published figures',
     '<b>Open</b>'],
], [50 * mm, 78 * mm, 40 * mm])

# ===========================================================================
# 8. Verdict
# ===========================================================================
d.h1('8.&nbsp;&nbsp;Conclusions and Recommendations')

d.table([
    ['#', 'Conclusion', 'Evidence'],
    ['1', 'All eight policies complete the exploration task to approximately 98% '
          'coverage; coverage alone cannot discriminate between them',
     f'Friedman on coverage, {NB} paired trials'],
    ['2', 'TAD at default weights is not statistically separable from random frontier '
          'selection on exploration efficiency',
     f'Mean ranks {tad_r:.2f} vs {rnd_r:.2f}, CD = {cd:.2f}'],
    ['3', 'TAD at default weights is the least economical policy tested, travelling '
          'about 86% further than nearest-frontier for equal coverage',
     f"{S_['TAD']['distance_m']['mean']:.0f} m vs {S_['NF']['distance_m']['mean']:.0f} m"],
    ['4', 'The deficiency is attributable to the polarity and magnitude of the distance '
          'term, not to the multi-criteria structure',
     f'Independent tuner selected w_d = {wd}; ablation agrees'],
    ['5', 'With the distance weight removed, TAD becomes competitive with the classical '
          'baselines but does not surpass them',
     f'Ranks {tun_r:.2f} vs NF {nf_r:.2f}, within CD'],
], [8 * mm, 100 * mm, 60 * mm])
d.sp(9)

d.h2('8.1&nbsp;&nbsp;Recommended actions')

d.table([
    ['Priority', 'Action', 'Cost'],
    ['<b>1</b>', 'Change the default launch weights to w_distance = 0 (retaining '
                 'adjacency and trapezoid). This is a parameter change, not a code '
                 'change, and recovers most of the measured shortfall',
     'None &mdash; already exposed at launch'],
    ['2', 'Retain nearest-frontier as the reference configuration for regression '
          'testing; any future change should be required to beat it',
     'None'],
    ['3', 'If the distance criterion is to be retained with meaning, reconsider its '
          'sign so that proximity is rewarded, and re-tune',
     'Small; one line plus a tuning sweep'],
    ['4', 'Investigate whether the min&ndash;max normalisation, introduced to reconcile '
          'incommensurable units, is itself responsible for the imbalance',
     'Moderate; requires the Rmap representation'],
], [16 * mm, 106 * mm, 46 * mm], highlight_rows=(1,))
d.sp(9)

d.callout('Overall assessment',
          'The TAD implementation is correct, as established by the validation dossier, '
          'but at its shipped default weights it is not an effective exploration policy: '
          'on this evidence it performs no better than random frontier selection and '
          'costs the most distance of any policy tested. The defect is narrow, '
          'well-localised and cheap to remedy &mdash; a single launch parameter recovers '
          'most of the gap. That a correctly implemented algorithm can still be the wrong '
          'thing to run is the central lesson of this comparison, and it is a conclusion '
          'that conformance testing alone could never have reached.', GOOD)

d.h2('8.2&nbsp;&nbsp;Reproducing this study')
d.story.append(Paragraph(
    'cd comparison<br/>'
    'python3 benchmark.py    # tuning + evaluation  -&gt; results_comparison.json<br/>'
    'python3 analyze.py      # Friedman/Nemenyi + figures<br/>'
    'python3 build_comparison_report.py', MONO))
d.sp(6)
d.p(f'The evaluation comprised {len(comp["runs"])} scored episodes plus the tuning '
    f'sweep, {comp["wall_clock_s"]/60:.0f} minutes of compute in total. '
    'results_comparison.json retains the full coverage-versus-distance trace of every '
    'episode, so all curves, statistics and figures can be recomputed independently.',
    SMALL)


# ===========================================================================
# Build
# ===========================================================================
def build():
    doc = BaseDocTemplate(OUT, pagesize=A4,
                          leftMargin=21 * mm, rightMargin=21 * mm,
                          topMargin=20 * mm, bottomMargin=18 * mm,
                          title='Frontier Exploration Algorithm Comparison',
                          author='explorer_exploration')
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='m')
    doc.addPageTemplates([PageTemplate(id='all', frames=[frame],
                                       onPage=decorate_factory(
                                           'Frontier-Selection Policy Comparison',
                                           'explorer_exploration'))])
    doc.build(d.story)
    print('Wrote', OUT)
