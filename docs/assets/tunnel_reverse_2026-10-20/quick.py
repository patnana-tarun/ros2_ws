"""Quick smoke summary: driving-mode shares by width class and by active controller, spins, start-up turn."""
import json, sys, math, numpy as np
for f in sys.argv[1:]:
    d = json.load(open(f)); S = d['samples']
    def share(sel):
        v = np.array([s['vx'] for s in sel]); w = np.array([s['wz'] for s in sel])
        if not len(v): return '-'
        rev = (v < -0.02).mean(); fwd = (v > 0.02).mean(); spot = ((abs(v) <= 0.02) & (abs(w) > 0.2)).mean()
        return f'n={len(v):4d} reverse {rev*100:5.1f}%  forward {fwd*100:5.1f}%  on-the-spot {spot*100:5.1f}%'
    print(f, d['stop_reason'], f"cov {d['cov'][-1] if isinstance(d['cov'],list) else d['cov']}")
    print('  open (>2.0)  ', share([s for s in S if s['width'] > 2.0]))
    print('  tunnel (<1.2)', share([s for s in S if s['width'] < 1.2]))
    for c in ('FollowPath', 'FollowPathReverse'):
        print(f'  ctrl {c:18s}', share([s for s in S if s.get('ctrl') == c]))
    # spins: >=300 deg turned within 60 s while net move < 1 m
    t = np.array([s['t'] for s in S]); yaw = np.unwrap([s['yaw'] for s in S]); xy = np.array([[s['x'], s['y']] for s in S])
    ev, last = 0, -1e9
    for i in range(len(t)):
        j = np.searchsorted(t, t[i] - 60)
        turned = np.abs(np.diff(yaw[j:i + 1])).sum()
        if turned >= math.radians(300) and np.linalg.norm(xy[i] - xy[j]) < 1 and t[i] - last > 60: ev += 1; last = t[i]
    k = np.searchsorted(t, 45)
    print(f'  spins {ev}   start-up turning (first 45 s) {math.degrees(np.abs(np.diff(yaw[:k])).sum()):.0f} deg')
