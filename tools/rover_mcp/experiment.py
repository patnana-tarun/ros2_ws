#!/usr/bin/env python3
"""A/B experiment harness: one YAML spec instead of a new recorder + runner script per experiment.

    experiment.py SPEC.yaml OUT_DIR          (normally started by the MCP tool experiment_start)

Spec:
    name: tunnel_reverse_vs_demo
    n: 3                      # runs per arm, interleaved (a_1 b_1 a_2 b_2 ...) so arms share machine state
    cap_s: 2400               # sim-time cap per run (40 min)
    common_args: "stall_timeout:=30.0"
    stop: {target_pct: 90, stuck_min_pct: 75, stuck_window_s: 180, stuck_gain_m2: 0.5}
    arms:
      trr:  {launch: tunnel_reverse.launch.py, args: ""}
      demo: {launch: bringup.launch.py, args: "params_file:=... bt_xml:=explore_nav_to_pose_demo.xml"}

Protocol as the 2026-10-18..20 comparisons: GUI runs; a run starts at the first /plan and stops at
the first of 90 % true-floor coverage ('reached_90'), >= 75 % with < 0.5 m2 gained in 180 s
('stuck_after_most'), the cap ('cap'), exploration_complete ('complete'), or the launch dying
('launch_exited'). Each run writes <tag>/launch.log, summary.json (compact), track.npz (10 Hz track,
map, coverage curve, goal events) and trajectory.png. At the end: comparison.md + comparison.png.
"""
import json
import math
import os
import signal
import sys
import time

import numpy as np
import yaml

import rosview
import simproc

STOP = {'target_pct': 90.0, 'stuck_min_pct': 75.0, 'stuck_window_s': 180.0, 'stuck_gain_m2': 0.5}
abort = False


def on_int(*_):
    global abort
    abort = True


def write_progress(out, d):
    tmp = os.path.join(out, 'progress.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(d, f, indent=1, default=str)
    os.replace(tmp, os.path.join(out, 'progress.json'))


def one_run(w, spec, arm, tag, out, idx, total, done):
    a = spec['arms'][arm]
    stop = {**STOP, **(spec.get('stop') or {})}
    cap = float(spec.get('cap_s', 2400))
    rd = os.path.join(out, tag)
    os.makedirs(rd, exist_ok=True)
    argv = ['ros2', 'launch', a.get('package', 'explorer_exploration'), a['launch']] + \
        (spec.get('common_args', '') + ' ' + a.get('args', '')).split()
    log = os.path.join(rd, 'launch.log')
    w.reset(launch_log=log)
    p = simproc.start(argv, log)
    w0 = time.time()
    print(f'{tag}: start {time.strftime("%H:%M:%S")}  {" ".join(argv)}', flush=True)
    reason, t_start = None, None
    while not abort:
        time.sleep(1.0)
        alive = p.poll() is None
        if not alive:
            reason = 'launch_exited'
            break
        if t_start is None:
            t_start = w.first_plan_t
            if t_start is None and time.time() - w0 > 240:
                reason = 'no_start'
                break
            prog = {'run': tag, 'index': idx, 'total': total, 'phase': 'starting', 'wall_s': round(time.time() - w0)}
            write_progress(out, {**prog, 'finished': done})
            continue
        el = w.now() - t_start
        with w.lock:
            cov = list(w.cov)
        c = cov[-1] if cov else None
        if c and c[3] >= stop['target_pct']:
            reason = 'reached_%d' % stop['target_pct']
        elif c and c[3] >= stop['stuck_min_pct']:
            old = [q for q in cov if q[0] <= c[0] - stop['stuck_window_s']]
            if old and c[2] - old[-1][2] < stop['stuck_gain_m2']:
                reason = 'stuck_after_most'
        if w.complete_t is not None:
            reason = reason or 'complete'
        if el >= cap:
            reason = reason or 'cap'
        if time.time() - w.last_sim_change > 30:
            reason = 'sim_stopped'      # Gazebo window closed / exited: rerun, does not count
        alerts = [x['kind'] for x in w.health(alive)]
        write_progress(out, {'run': tag, 'index': idx, 'total': total, 'phase': 'running',
                             'sim_s': round(el), 'wall_s': round(time.time() - w0),
                             'coverage_pct': round(c[3], 1) if c else None, 'alerts': alerts,
                             'finished': done})
        if reason:
            break
    reason = reason or 'aborted'
    t1 = w.now()
    t0 = t_start if t_start is not None else (w.samples[0]['t'] if w.samples else t1)
    summ = w.summarize(t0, t1)
    with w.lock:
        cov = list(w.cov)
        m = w.map
    curve = [(round(q[0] - t0, 1), round(q[3], 2)) for q in cov if q[0] >= t0]
    curve = curve[::max(1, len(curve) // 200)]
    res = {'tag': tag, 'arm': arm, 'cmd': ' '.join(argv), 'stop_reason': reason,
           'duration_s': round(t1 - t0, 1), 'wall_s': round(time.time() - w0),
           'final_coverage_pct': round(cov[-1][3], 1) if cov else None,
           'time_to_target_s': next((t for t, pc in curve if pc >= stop['target_pct']), None),
           'node_died': [d[1] for d in w.died][:5], 'metrics': summ, 'coverage_curve': curve}
    with open(os.path.join(rd, 'summary.json'), 'w') as f:
        json.dump(res, f, indent=1, default=str)
    tr = w.track_array()
    if m is not None:
        tr.update(map=rosview._grid(m).astype(np.int8), map_res=m.info.resolution,
                  map_origin=np.array([m.info.origin.position.x, m.info.origin.position.y]))
        np.savez_compressed(os.path.join(rd, 'track.npz'), **tr)
        try:
            k = tr['t'] >= t0
            data = {kk: (v[k] if isinstance(v, np.ndarray) and v.shape[:1] == tr['t'].shape else v)
                    for kk, v in tr.items()}
            png = rosview.render(data=data, title_extra=f'   {tag}: {reason}')
            with open(os.path.join(rd, 'trajectory.png'), 'wb') as f:
                f.write(png)
        except Exception as e:
            print(f'{tag}: figure failed: {e}', flush=True)
    simproc.stop(p)
    print(f'{tag}: done  {reason}  {res["duration_s"] / 60:.1f} min  coverage {res["final_coverage_pct"]} %', flush=True)
    time.sleep(3)
    return res


def main():
    spec_path, out = sys.argv[1], sys.argv[2]
    spec = yaml.safe_load(open(spec_path))
    signal.signal(signal.SIGINT, on_int)
    signal.signal(signal.SIGTERM, on_int)
    w = rosview.watcher()
    simproc.stop(None)       # stale sims in our partition
    n = int(spec.get('n', 2))
    order = [(arm, f'{arm}_{i}') for i in range(1, n + 1) for arm in spec['arms']]
    done = []
    for idx, (arm, tag) in enumerate(order, 1):
        if abort:
            break
        r = one_run(w, spec, arm, tag, out, idx, len(order), done)
        if r['stop_reason'] in ('sim_stopped', 'no_start') and not abort:
            os.rename(os.path.join(out, tag), os.path.join(out, f'{tag}_void_{r["stop_reason"]}'))
            print(f'{tag}: {r["stop_reason"]} - does not count, running it again', flush=True)
            r = one_run(w, spec, arm, tag, out, idx, len(order), done)
        done.append({'tag': tag, 'stop': r['stop_reason'], 'min': round(r['duration_s'] / 60, 1),
                     'cov': r['final_coverage_pct']})
    write_progress(out, {'phase': 'aborted' if abort else 'finished', 'finished': done})
    import compare
    md, _ = compare.compare([out], out)
    print(open(md).read(), flush=True)
    print('ALL_DONE', flush=True)
    os._exit(0)


if __name__ == '__main__':
    main()
