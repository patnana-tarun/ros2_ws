#!/usr/bin/env python3
"""Builds the two presentation pages of the mesh field tests (view only, no analysis tools):

  ../field_tests_case1.html     Case 1: direct link, explorer moves away from the base station
  ../field_tests_case2_3.html   Case 2: relay range; Case 3: relay fixed, explorer moves beyond it

Numbers come from the report's field-test analysis (reports/review_3/scripts/comm_analysis.py),
so the pages match the report. Plotly is embedded, so the pages also work offline.
The Q chart can switch weight set: the five sets in weights.csv next to this script (output of
../../weights/weights_calculator_kit on the two main field-test files, --exclude 6 7 8 42;
subjective, the one used, is the default) applied to the report's S terms.
Usage: python3 make_pages.py
"""
import csv, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '../../../reports/review_3/scripts')))
import comm_analysis as ca  # noqa: E402

N1_POS = 48  # relay fixed at unit 48 in case 3
WEIGHTS_CSV = os.path.join(HERE, 'weights.csv')
TERMS = ['map_gap', 'map_lat', 'tf_pdr', 'tf_lat']          # order of comm_analysis terms
SET_LABEL = {'subjective': 'Subjective (used)', 'AHP': 'AHP', 'CRITIC': 'CRITIC', 'Entropy': 'Entropy', 'MEREC': 'MEREC'}


def weight_sets():
    """[{name, label, w: [gap, lat, tfpdr, tflat]}] from the kit's weights.csv, subjective first."""
    with open(WEIGHTS_CSV) as fh:
        rows = {r['']: r for r in csv.DictReader(fh)}
    names = [n for n in next(iter(rows.values())) if n]
    sets = [dict(name=n, label=SET_LABEL.get(n, n), w=[float(rows[t][n]) for t in TERMS]) for n in names]
    assert sets[0]['name'] == 'subjective' and np.allclose(sets[0]['w'], ca.WEIGHTS), 'subjective weights differ from the report'
    return sets


def r(v, d=1):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), d)


def mean10(x):
    out = []
    for i in range(len(x)):
        w = x[max(0, i - 9):i + 1]
        w = w[~np.isnan(w)]
        out.append(r(w.mean()) if len(w) else None)
    return out


def run_series(rs):
    st = ca.run_stats(rs)
    t = st['t'] - st['t'][0]
    act = [row['map_active'] == '1' for row in rs]
    age, last = [], None
    for ti, a in zip(t, act):
        if a:
            last = ti
        age.append(r(ti - last) if last is not None else None)
    return dict(t=[r(v) for v in t], age=age, rssi=mean10(st['rssi']),
                maplat=[r(v, 0) for v in st['map_lat']], tfpdr=[r(v) for v in st['tf_pdr']],
                maps=[r(v) for v, a in zip(t, act) if a], kmax=ca.k_of(st['max_gap']),
                delivery=r(100 * st['n_maps'] / st['due'], 0))


def scenario(s, d, runs, sets):
    pos = ca.POS[s]
    if ca.CASE[s] == 1:
        layout = dict(laptop=pos, n1=None)
    elif ca.CASE[s] == 2:
        layout = dict(laptop=pos, n1=pos)
    else:
        layout = dict(laptop=N1_POS + pos, n1=N1_POS)
    return dict(
        id=s, case=ca.CASE[s], length=r(pos * ca.UNIT, 2), layout=layout,
        delivery=r(100 * d['delivery'], 0), gap_med=r(d['gap_med']), gap_max=r(d['gap_max'], 0),
        kmax=int(d['kmax']), maplat=r(d['maplat_med'], 0), maplat90=r(d['maplat_p90'], 0),
        tfpdr=r(d['tfpdr_mean']), tflat=r(d['tflat_med'], 0), rssi=r(d['rssi_med']),
        tq=r(d['tq_med'], 0), pdr=r(d['pdr_med']), q=r(d['Q'], 2), terms=[r(v, 2) for v in d['terms']],
        qs={ws['name']: r(np.dot(ws['w'], d['terms']), 2) for ws in sets},
        share=[r(v, 3) for v in d['share']], verdict=ca.verdict(d),
        runs=[dict(id=rid, **run_series(rs)) for (sc, rid), rs in sorted(runs.items()) if sc == s])


CASES = {
    1: dict(name='Case 1', title='Direct link', short='direct link',
            question='How far does a direct explorer–base link carry the map?',
            link='explorer ↔ base', length_label='Explorer–base distance',
            rssi_label='RSSI of the base station, heard at the explorer'),
    2: dict(name='Case 2', title='Relay range', short='relay moved',
            question='How far can the relay be from the base station?',
            link='relay ↔ base', length_label='Relay–base distance',
            rssi_label='RSSI of the base station, heard at the relay'),
    3: dict(name='Case 3', title='Relay fixed, explorer beyond it', short='relay fixed',
            question='How far can the explorer go past a relay?',
            link='explorer ↔ relay', length_label='Explorer–relay distance',
            rssi_label='RSSI of the relay, heard at the explorer'),
}


def build(cases, out_name, page_title):
    runs = ca.load()
    tab = ca.scenario_table(runs)
    sets = weight_sets()
    data = dict(unit=ca.UNIT, weights=[dict(ws, w=[round(v, 3) for v in ws['w']]) for ws in sets], cases={})
    for c in cases:
        data['cases'][c] = dict(CASES[c], scenarios=[scenario(s, tab[s], runs, sets) for s in ca.SCEN if ca.CASE[s] == c])
    with open(os.path.join(HERE, 'template.html')) as fh:
        html = fh.read()
    with open(os.path.join(HERE, 'plotly-2.27.0.min.js')) as fh:
        plotly = fh.read()
    html = (html.replace('__PAGE_TITLE__', page_title)
                .replace('/*__DATA__*/null', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
                .replace('/*__PLOTLY__*/', plotly))
    out = os.path.normpath(os.path.join(HERE, '..', out_name))
    with open(out, 'w') as fh:
        fh.write(html)
    print(f'wrote {out} ({os.path.getsize(out) / 1e6:.1f} MB)')


if __name__ == '__main__':
    build([1], 'field_tests_case1.html', 'Field Tests: Direct Link')
    build([2, 3], 'field_tests_case2_3.html', 'Field Tests: Relay Node')
