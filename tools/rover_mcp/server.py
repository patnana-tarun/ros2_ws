"""rover MCP server: lets Claude run, watch, judge and tune the explorer in Gazebo + RViz.

Self-correction loop (see tools/rover_mcp/README.md and docs/concepts/Tuning loop.md):
  preflight -> smoke_test -> observe (stops early on an alert, with evidence) -> diagnose
  (logs, map_view, screenshot, ros2/gz) -> change (set_params live, or edit YAML + build) ->
  smoke_test -> experiment (n runs per arm, same stop rules as the report) -> compare.
Every run gets a folder tools/rover_mcp/runs/<time>_<label>/ with launch.log, journal.jsonl
(every action and observation), screenshots, map renders, track.npz and summary.json.
Started by run.sh, which applies simenv.sh (isolated ROS domain + GZ partition, snap-free GUI env).
"""
import asyncio
import atexit
import datetime
import glob
import io
import json
import os
import re
import shlex
import signal
import subprocess
import time

import anyio
import numpy as np
import yaml
from mcp.server.fastmcp import Context, FastMCP, Image
from PIL import Image as PILImage, ImageDraw

import rosview
import simproc
import x11win

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, '..', '..'))
RUNS = os.path.join(HERE, 'runs')
PY = os.path.join(HERE, '.venv', 'bin', 'python')
mcp = FastMCP('rover', instructions=(
    'Run, watch and tune the explorer rover in Gazebo/RViz (ROS 2 Jazzy, Nav2, SLAM Toolbox). '
    'Loop: preflight -> smoke_test -> observe (returns early with evidence when an alert fires) -> '
    'diagnose with logs/map_view/screenshot -> change one thing (set_params, or edit YAML then build) -> '
    'smoke_test -> experiment for A/B claims -> experiment_status/compare. Path accuracy (xte, heading '
    'deviation, rotation events, plans through unknown) ranks above speed. Never claim an improvement '
    'from one observe window: confirm with an experiment (n >= 2 per arm, GUI runs).'))

SIM = {'proc': None, 'dir': None, 'cmd': None, 'started': None}
EXP = {'proc': None, 'dir': None}
SCALE = {}          # window id -> scale of the last screenshot (image px = window px * scale)


def run_dir():
    # during an experiment, journal entries and pictures belong to its current run, not the last sim_start
    if exp_running():
        try:
            with open(os.path.join(EXP['dir'], 'progress.json')) as f:
                d = os.path.join(EXP['dir'], json.load(f).get('run') or '')
            if os.path.isdir(d):
                return d
        except (OSError, ValueError):
            pass
        return EXP['dir']
    if SIM['dir'] is None:
        SIM['dir'] = os.path.join(RUNS, datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '_external')
        os.makedirs(SIM['dir'], exist_ok=True)
    return SIM['dir']


def stamp():
    return datetime.datetime.now().strftime('%H%M%S')


def journal(kind, **kw):
    # at sim_start the node clock still holds the previous sim's last /clock
    sim_t = None if kind == 'sim_start' else round(rosview.watcher().now(), 1)
    with open(os.path.join(run_dir(), 'journal.jsonl'), 'a') as f:
        f.write(json.dumps({'wall': datetime.datetime.now().isoformat(timespec='seconds'), 'kind': kind,
                            'sim_t': sim_t, **kw}, default=str) + '\n')


def jdump(o):
    return json.dumps(o, indent=1, default=str)


def sim_running():
    return SIM['proc'] is not None and SIM['proc'].poll() is None


def exp_running():
    return EXP['proc'] is not None and EXP['proc'].poll() is None


def _exclude():
    return [EXP['proc'].pid] if exp_running() else []


def _save_track():
    w = rosview.watcher()
    tr = w.track_array()
    if len(tr['t']) == 0:
        return None
    with w.lock:
        m = w.map
    if m is not None:
        tr.update(map=rosview._grid(m).astype(np.int8), map_res=m.info.resolution,
                  map_origin=np.array([m.info.origin.position.x, m.info.origin.position.y]))
    path = os.path.join(run_dir(), 'track.npz')
    np.savez_compressed(path, **tr)
    t = tr['t']
    with open(os.path.join(run_dir(), 'summary.json'), 'w') as f:
        json.dump({'cmd': SIM['cmd'], 'whole_run': w.summarize(t[0], t[-1]), 'final_state': w.state()},
                  f, indent=1, default=str)
    return path


def _on_exit():
    if os.environ.get('ROVER_MCP_KEEP_SIM') != '1' and SIM['proc'] is not None:
        try:
            _save_track()
        except Exception:
            pass
        simproc.stop(SIM['proc'], grace=6.0, exclude=_exclude())
    rosview.shutdown()


atexit.register(_on_exit)
signal.signal(signal.SIGTERM, lambda *a: (_on_exit(), os._exit(0)))


async def _sh(argv, timeout, cwd=None):
    def go():
        p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True,
                             env=os.environ.copy(), cwd=cwd)
        try:
            out, _ = p.communicate(timeout=timeout)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGINT)
            try:
                out, _ = p.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                out, _ = p.communicate()
            rc = f'timeout after {timeout}s (output so far below)'
        txt = out.decode(errors='replace')
        if len(txt) > 12000:
            txt = txt[:4000] + f'\n... [{len(txt) - 8000} chars cut] ...\n' + txt[-4000:]
        return f'exit {rc}\n{txt}'
    return await anyio.to_thread.run_sync(go)


def _tail(n=40, grep=None):
    p = os.path.join(run_dir(), 'launch.log')
    if not os.path.exists(p):
        return '(no launch.log: sim not started by this server)'
    with open(p, errors='replace') as f:
        lines = [re.sub(r'\x1b\[[0-9;]*m', '', l) for l in f.readlines()]
    if grep:
        rx = re.compile(grep, re.I)
        lines = [l for l in lines if rx.search(l)]
    return ''.join(lines[-n:])


# ---------------------------------------------------------------- preflight
def _stale_installs():
    """src files whose installed copy differs (edited but not rebuilt -> the change is not in effect)."""
    stale = []
    for pkg_dir in glob.glob(os.path.join(WS, 'src', '*')):
        pkg = os.path.basename(pkg_dir)
        inst = os.path.join(WS, 'install', pkg)
        if not os.path.isdir(inst):
            stale.append(f'{pkg}: not installed')
            continue
        idx = {}
        for root, _, files in os.walk(inst):
            for fn in files:
                idx.setdefault(fn, []).append(os.path.join(root, fn))
        for root, dirs, files in os.walk(pkg_dir):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', 'test', 'resource')]
            for fn in files:
                if not fn.endswith(('.py', '.yaml', '.xml', '.xacro', '.sdf', '.urdf', '.rviz', '.config')) \
                        or fn in ('setup.py', 'package.xml'):
                    continue
                src = os.path.join(root, fn)
                rel = os.path.relpath(src, pkg_dir)
                cands = [c for c in idx.get(fn, []) if c.endswith(rel) or c.endswith(os.path.join(pkg, fn))]
                cands = cands or idx.get(fn, [])
                if not cands:
                    continue
                with open(src, 'rb') as a:
                    sb = a.read()
                if not any(open(c, 'rb').read() == sb for c in cands):
                    stale.append(f'{pkg}/{rel}')
    return stale


@mcp.tool()
async def preflight():
    """Check the things that broke earlier sessions before spending time on a run: snap GUI env
    (gz/rviz crash), discovery/domain isolation, stale or foreign sim processes, GPU offload, USB
    tether (gz multicast 'No such device'), src edits not built into install/, git branch."""
    R = {}
    bad = [k for k in ('GTK_PATH', 'GTK_EXE_PREFIX', 'LOCPATH', 'GIO_MODULE_DIR') if os.environ.get(k)]
    R['gui_env'] = 'OK' if not bad and '/snap/' not in os.environ.get('XDG_DATA_DIRS', '') else f'SNAP VARS SET: {bad}'
    R['ros_isolation'] = {k: os.environ.get(k) for k in ('ROS_DOMAIN_ID', 'ROS_AUTOMATIC_DISCOVERY_RANGE',
                                                         'ROS_DISCOVERY_SERVER', 'GZ_PARTITION', 'RMW_IMPLEMENTATION')}
    R['our_partition_processes'] = [f'{p} {simproc.cmdline(p)[:100]}' for p in simproc.partition_pids(_exclude())][:15]
    foreign = []
    for p in os.listdir('/proc'):
        if p.isdigit():
            c = simproc.cmdline(int(p))
            if re.search(r'gz sim|rviz2|ruby .*gz', c) and int(p) not in simproc.partition_pids(_exclude()):
                foreign.append(f'{p} {c[:100]}')
    R['other_sims_running (GPU/CPU contention)'] = foreign[:10]
    gpu = await _sh(['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used,memory.total',
                     '--format=csv,noheader'], 10)
    procs = await _sh(['nvidia-smi'], 10)
    R['gpu'] = gpu.split('\n', 1)[-1].strip()
    R['gpu_processes'] = [l.strip() for l in procs.splitlines() if re.search(r'gz|ruby|rviz|ogre', l)][:8]
    R['gpu_offload_env'] = os.environ.get('__NV_PRIME_RENDER_OFFLOAD') == '1'
    links = await _sh(['ip', '-br', 'link'], 5)
    R['usb_tether_links (first suspect for gz multicast ENODEV)'] = [
        l.split()[0] for l in links.splitlines()[1:] if re.match(r'(usb|enx|rndis)', l.split()[0] if l.split() else '')]
    st = await anyio.to_thread.run_sync(_stale_installs)
    R['src_not_built_into_install'] = st[:30] or 'none'
    br = await _sh(['git', '-C', WS, 'branch', '--show-current'], 5)
    dirty = await _sh(['git', '-C', WS, 'status', '--short', '--', 'src', 'tools', 'docs'], 5)
    R['git_branch'] = br.split('\n', 1)[-1].strip()
    R['git_dirty_files'] = [l for l in dirty.splitlines()[1:] if l.strip()][:20]
    if R['git_branch'] == 'feat/demo':
        R['git_warning'] = 'feat/demo must stay clean: experiment on an exp/* branch'
    R['experiment_running'] = exp_running()
    problems = [k for k, v in R.items() if (isinstance(v, str) and ('SET' in v or 'warning' in k))
                or (k.startswith('src_not_built') and v != 'none')
                or (k.startswith('our_partition') and v and not sim_running())
                or (k.startswith('other_sims') and v)]
    return jdump({'problems': problems, **R})


@mcp.tool()
async def build(packages: str = 'explorer_exploration'):
    """colcon build --packages-select <packages> (space-separated) in the workspace. Needed after editing
    YAML/launch/Python in src/ (no symlink install): a running sim keeps the old files until restarted."""
    out = await _sh(['colcon', 'build', '--packages-select'] + packages.split(), 900, cwd=WS)
    journal('build', packages=packages, ok=out.startswith('exit 0'))
    st = await anyio.to_thread.run_sync(_stale_installs)
    return out[-3000:] + f'\nsrc files still differing from install/: {st[:20] or "none"}'


# ---------------------------------------------------------------- sim lifecycle
async def _start(ctx, launch, args, package, label, wait_ready):
    if exp_running():
        return False, 'an experiment is running (experiment_status / experiment_stop first)'
    simproc.stop(SIM['proc'], exclude=_exclude())
    tag = re.sub(r'[^A-Za-z0-9_.-]+', '_', label or launch.replace('.launch.py', ''))
    SIM['dir'] = os.path.join(RUNS, datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + tag)
    os.makedirs(SIM['dir'], exist_ok=True)
    argv = ['ros2', 'launch', package, launch] + shlex.split(args)
    SIM['cmd'] = ' '.join(argv)
    log = os.path.join(SIM['dir'], 'launch.log')
    w = rosview.watcher()
    w.reset(launch_log=log)
    SIM['proc'] = simproc.start(argv, log)
    SIM['started'] = time.time()
    journal('sim_start', cmd=SIM['cmd'])
    msg = f'started pid {SIM["proc"].pid}: {SIM["cmd"]}\nrun folder: {SIM["dir"]}'
    if not wait_ready:
        return True, msg
    for i in range(150):
        await asyncio.sleep(1.0)
        await ctx.report_progress(i, 150)
        if not sim_running():
            return False, msg + f'\nLAUNCH EXITED (code {SIM["proc"].returncode}). Tail of log:\n' + _tail(40)
        if w.map is not None and w.samples:
            return True, msg + f'\nready after {i + 1} s: /map and pose arriving.\n' + jdump(w.state())
    return False, msg + '\nnot ready after 150 s (no /map or no map->base_footprint TF). Log tail:\n' + _tail(30)


@mcp.tool()
async def sim_start(ctx: Context, launch: str = 'tunnel_reverse.launch.py', args: str = '',
                    package: str = 'explorer_exploration', label: str = '', wait_ready: bool = True):
    """Start a sim launch (Gazebo + Nav2 + exploration; RViz unless args has rviz:=false) in the isolated
    env, logging to a fresh run folder. Replaces any sim in our partition. args: launch arguments,
    e.g. "world:=cave.sdf stall_timeout:=30.0". wait_ready: wait (<= 150 s) for /map and the robot pose."""
    return (await _start(ctx, launch, args, package, label, wait_ready))[1]


@mcp.tool()
def sim_stop(save: bool = True):
    """Stop the sim (SIGINT to the launch, then kill), save track.npz + summary.json to the run folder."""
    path = _save_track() if save else None
    had = SIM['proc'] is not None
    journal('sim_stop')
    simproc.stop(SIM['proc'], exclude=_exclude())
    SIM['proc'] = None
    left = simproc.partition_pids(_exclude())
    return (f'{"stopped" if had else "no sim of ours was running; cleaned partition"}. '
            f'saved: {path}. run folder: {SIM["dir"]}' + (f'\nstill alive: {left}' if left else ''))


@mcp.tool()
def sim_status():
    """Is the sim running, current alerts, the robot state, and recent launch-log errors."""
    w = rosview.watcher()
    st = {'launch': SIM['cmd'], 'running': sim_running(),
          'exit_code': None if SIM['proc'] is None else SIM['proc'].poll(),
          'wall_elapsed_s': round(time.time() - SIM['started'], 0) if SIM['started'] else None,
          'run_dir': SIM['dir'], 'alerts': w.health(sim_running() if SIM['proc'] else None),
          'state': w.state()}
    return jdump(st) + '\n--- recent ERROR/WARN lines in launch.log ---\n' + _tail(12, r'error|warn|fatal|died|exception')


@mcp.tool()
async def smoke_test(ctx: Context, launch: str = 'tunnel_reverse.launch.py', args: str = '',
                     seconds: float = 150.0, keep_running: bool = False):
    """Pass/fail gate after any change, before longer runs: launch, then within `seconds` of sim time
    check robot spawned + TF, /map, Nav2 planned, drove >= 1.5 m, no node died. Rotation events,
    large deviation, stalls and plans through unknown are warnings, not failures (the start-up
    U-turn of tunnel_reverse counts as a rotation event). Returns the verdict, metrics, map and a
    Gazebo screenshot. Stops the sim unless keep_running."""
    ok, msg = await _start(ctx, launch, args, 'explorer_exploration', 'smoke', True)
    w = rosview.watcher()
    t0 = w.now()
    w0 = time.time()
    if ok:
        while w.now() - t0 < seconds and time.time() - w0 < 3 * seconds + 60:
            await asyncio.sleep(1.0)
            await ctx.report_progress(min(w.now() - t0, seconds), seconds)
            if not sim_running() or w.died:
                break
    passed, checks = rosview.smoke_verdict(w, sim_running())
    summ = w.summarize(w.samples[0]['t'], w.now()) if w.samples else {}
    for k in ('top_messages', 'controller_switches'):
        summ.pop(k, None)
    journal('smoke_test', passed=passed, checks=checks)
    out = [f'SMOKE {"PASS" if passed else "FAIL"}\n' + jdump(checks) + '\n' + msg.split('\n')[0]
           + f'\nmetrics: {jdump(summ)}\nalerts: {jdump(w.health(sim_running()))}']
    out += _evidence(['map', 'gazebo'])
    if not passed:
        out.append('launch log errors:\n' + _tail(25, r'error|fatal|died|exception|symbol lookup'))
    if not keep_running:
        _save_track()
        simproc.stop(SIM['proc'], exclude=_exclude())
        SIM['proc'] = None
    return out


# ---------------------------------------------------------------- watching
def _render_image(radius=None, last_seconds=None, costmap=True, name='map'):
    png = rosview.render(rosview.watcher(), radius=radius, last_s=last_seconds, costmap=costmap)
    path = os.path.join(run_dir(), f'{name}_{stamp()}.png')
    with open(path, 'wb') as f:
        f.write(png)
    return Image(data=png, format='png'), path


def _evidence(kinds, radius=4.0):
    out = []
    for k in kinds:
        try:
            if k == 'map':
                img, p = _render_image(radius=radius, last_seconds=120, name='evidence_map')
                out += [img, f'map around the robot (last 120 s of track): {p}']
            else:
                data, _, desc = _shot(k, False, 1200)
                out += [Image(data=data, format='jpeg'), desc]
        except Exception as e:
            out.append(f'(no {k} evidence: {e})')
    return out


@mcp.tool()
def robot_state():
    """Pose (map frame), odom and commanded velocity, controller, xte/heading error, goal and last goal
    event, coverage, last plan (unknown/lethal share), topic rates."""
    return jdump(rosview.watcher().state())


@mcp.tool()
async def observe(ctx: Context, seconds: float = 60.0, stop_on_alert: bool = True, render: bool = True,
                  radius: float = 0.0, evidence: str = 'map,gazebo'):
    """Let the sim run `seconds` of SIM time (wall cap 4x, max 1200 s), then summarize that window with
    the report's metrics: tracking (xte, heading, large-deviation %; all/tunnel/open), rotation events,
    stall episodes, time budget, reverse metres, goal outcomes, plans through unknown/lethal cells,
    coverage gain, WARN/ERROR by node, alerts.
    stop_on_alert: return as soon as a new alert fires (not_moving, rotation, node_died, no_map,
    no_pose, no_clock, launch_exited), with evidence (comma list: map, gazebo, rviz)."""
    w = rosview.watcher()
    seconds = min(seconds, 1200.0)
    pre = {a['kind'] for a in w.health(sim_running() if SIM['proc'] else None)}
    t0, w0 = w.now(), time.time()
    fired = []
    while w.now() - t0 < seconds and time.time() - w0 < 4 * seconds:
        await asyncio.sleep(1.0)
        await ctx.report_progress(min(w.now() - t0, seconds), seconds)
        alerts = w.health(sim_running() if SIM['proc'] else None)
        fired = [a for a in alerts if a['kind'] in rosview.ALERTS_STOP and a['kind'] not in pre]
        if stop_on_alert and fired:
            break
    t1 = w.now()
    summ = w.summarize(t0, t1)
    summ['alerts'] = w.health(sim_running() if SIM['proc'] else None)
    if fired:
        summ['STOPPED_EARLY_ON'] = fired
    journal('observe', summary=summ)
    out = [jdump(summ)]
    if fired:
        out += _evidence([e.strip() for e in evidence.split(',') if e.strip()])
    elif render and w.map is not None:
        img, path = _render_image(radius=radius or None, name='observe')
        out = [img, out[0] + f'\nmap saved: {path}']
    return out


@mcp.tool()
def map_view(radius: float = 0.0, last_seconds: float = 0.0, costmap: bool = True):
    """Top-down render of /map + global costmap (orange inflation, red lethal) + track (green forward,
    red reverse, orange dots spin-in-place) + /plan (blue) + /plan_smoothed (cyan) + goal + robot.
    radius > 0 zooms around the robot; last_seconds > 0 shows only the recent track."""
    img, path = _render_image(radius=radius or None, last_seconds=last_seconds or None, costmap=costmap)
    return [img, f'saved: {path}']


@mcp.tool()
def logs(source: str = 'rosout', level: str = 'WARN', node: str = '', grep: str = '', last: int = 60,
         since_sim_s: float = -1.0):
    """Read logs. source='rosout': every node's /rosout since sim_start, filtered by min level
    (DEBUG/INFO/WARN/ERROR), node-name substring, text substring, sim-time start.
    source='goals': explore_coordinator goal events (sent/reached/gave_up/no_progress/retrace...).
    source='launch': tail of this run's launch.log (grep is a regex there)."""
    w = rosview.watcher()
    if source == 'launch':
        return _tail(last, grep or None)
    if source == 'goals':
        with w.lock:
            ev = list(w.events)[-last:]
        return '\n'.join(f'[{t:8.1f}] {k:20} {m}' for t, k, m in ev) or '(no goal events yet)'
    lv = {'DEBUG': 10, 'INFO': 20, 'WARN': 30, 'WARNING': 30, 'ERROR': 40, 'FATAL': 50}[level.upper()]
    rows = w.logs(lv, node or None, grep or None, since_sim_s if since_sim_s >= 0 else None, last)
    if not rows:
        return '(no matching /rosout entries)'
    return '\n'.join(f'[{t:8.1f}] {rosview.LEVELS.get(l, l):5} {n}: {m}' for t, _, l, n, m in rows)


# ---------------------------------------------------------------- CLIs and tuning
@mcp.tool()
async def ros2(args: str, timeout: float = 20.0):
    """Run `ros2 <args>` in the sim env, e.g. "topic hz /scan", "node list",
    "param get /controller_server FollowPath.vx_max", "topic echo /odom --once", "service list".
    Killed after `timeout` s (output so far is returned) - fine for hz/echo."""
    return await _sh(['ros2'] + shlex.split(args), timeout)


@mcp.tool()
async def gz(args: str, timeout: float = 15.0):
    """Run `gz <args>` in our Gazebo partition, e.g. "topic -l", "service -l", "model --list"."""
    return await _sh(['gz'] + shlex.split(args), timeout)


@mcp.tool()
async def set_params(node: str, params: dict, note: str = ''):
    """Set ROS parameters live and record old/new values with `note` (the hypothesis) in the journal.
    params: {"FollowPath.vx_max": 0.3, ...}. String values are YAML-parsed.
    A live change is lost on restart - copy keepers into the YAML, build, smoke_test."""
    res = {}
    for k, v in params.items():
        if isinstance(v, str):
            try:
                v = yaml.safe_load(v)
            except Exception:
                pass
        old = await _sh(['ros2', 'param', 'get', node, k], 10)
        # MCP clients send 0.0 as the JSON number 0; ROS refuses an integer for a double parameter
        if 'Double value is' in old and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        val = json.dumps(v) if not isinstance(v, str) else v
        r = await _sh(['ros2', 'param', 'set', node, k, val], 15)
        res[k] = {'old': old.split('\n', 1)[-1].strip(), 'new': v, 'result': r.split('\n', 1)[-1].strip()}
    journal('set_params', node=node, params=res, note=note)
    return jdump(res)


@mcp.tool()
def journal_note(text: str):
    """Add a note (hypothesis, observation, decision) to the run's journal.jsonl."""
    journal('note', text=text)
    return f'noted in {os.path.join(run_dir(), "journal.jsonl")}'


# ---------------------------------------------------------------- experiments
@mcp.tool()
def experiment_start(spec: str):
    """Start an A/B experiment in the background (tools/rover_mcp/experiment.py): arms x n runs,
    interleaved, GUI, stop at 90 % floor coverage / stuck above 75 % / cap, compact summaries,
    trajectory figures, comparison.md + comparison.png at the end.
    spec: path to a YAML spec, or the YAML text itself. Example:
      name: smac_vs_navfn
      n: 2
      cap_s: 2400
      arms:
        base:  {launch: tunnel_reverse.launch.py, args: ""}
        smac:  {launch: tunnel_reverse.launch.py, args: "params_file:=/abs/path/nav2_params_smac.yaml"}"""
    if exp_running():
        return f'experiment already running: {EXP["dir"]}'
    if sim_running():
        simproc.stop(SIM['proc'])
        SIM['proc'] = None
    text = open(spec).read() if os.path.exists(spec) else spec
    s = yaml.safe_load(text)
    d = os.path.join(RUNS, datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '_exp_' +
                     re.sub(r'[^A-Za-z0-9_.-]+', '_', s.get('name', 'exp')))
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'spec.yaml'), 'w') as f:
        f.write(text)
    log = open(os.path.join(d, 'runner.log'), 'w')
    EXP['proc'] = subprocess.Popen([PY, os.path.join(HERE, 'experiment.py'), os.path.join(d, 'spec.yaml'), d],
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                   env=os.environ.copy())
    EXP['dir'] = d
    n_runs = len(s['arms']) * int(s.get('n', 2))
    return f'experiment started (pid {EXP["proc"].pid}), {n_runs} runs, folder {d}. Poll experiment_status.'


@mcp.tool()
def experiment_status():
    """Progress of the running/last experiment: current run, sim time, coverage, alerts, finished runs."""
    d = EXP['dir'] or (sorted(glob.glob(os.path.join(RUNS, '*_exp_*'))) or [None])[-1]
    if d is None:
        return 'no experiment found'
    out = {'dir': d, 'runner_running': exp_running()}
    p = os.path.join(d, 'progress.json')
    if os.path.exists(p):
        out['progress'] = json.load(open(p))
    cmp_md = os.path.join(d, 'comparison.md')
    txt = jdump(out)
    if os.path.exists(cmp_md):
        txt += '\n\n' + open(cmp_md).read()
    log = os.path.join(d, 'runner.log')
    if os.path.exists(log):
        txt += '\n--- runner.log tail ---\n' + ''.join(open(log, errors='replace').readlines()[-12:])
    return txt


@mcp.tool()
def experiment_stop():
    """Stop the running experiment (the current run is saved as 'aborted')."""
    if not exp_running():
        return 'no experiment running'
    os.killpg(EXP['proc'].pid, signal.SIGINT)
    try:
        EXP['proc'].wait(40)
    except subprocess.TimeoutExpired:
        os.killpg(EXP['proc'].pid, signal.SIGKILL)
    simproc.stop(None)
    return f'stopped; folder {EXP["dir"]}'


@mcp.tool()
def compare(dirs: str, out: str = ''):
    """Compare finished runs: dirs = space-separated experiment folders (or run folders). Writes and
    returns comparison.md + comparison.png (per-arm mean, sd, n of the key metrics)."""
    import compare as cmp
    md, png = cmp.compare(dirs.split(), out or None)
    return [Image(path=png), open(md).read()]


# ---------------------------------------------------------------- Gazebo control
async def _gz_service(service, reqtype, reptype, req, timeout_ms=3000):
    return await _sh(['gz', 'service', '-s', service, '--reqtype', reqtype, '--reptype', reptype,
                      '--timeout', str(timeout_ms), '--req', req], timeout_ms / 1000 + 5)


async def _world():
    out = await _sh(['gz', 'service', '-l'], 10)
    m = re.search(r'^/world/([^/\s]+)/control$', out, re.M)
    return m.group(1) if m else None


@mcp.tool()
async def gz_camera(mode: str = 'follow', model: str = 'explorer', x: float = 0.0, y: float = 0.0,
                    z: float = 18.0, offset_x: float = -2.5, offset_z: float = 2.0):
    """Move the Gazebo GUI camera. mode: 'follow' (chase `model`; offset_x/offset_z behind/above),
    'unfollow', 'top' (straight down from height z over x, y), 'robot_top' (top view over the robot)."""
    if mode in ('follow', 'unfollow'):
        r = await _gz_service('/gui/follow', 'gz.msgs.StringMsg', 'gz.msgs.Boolean',
                              f'data: "{model if mode == "follow" else ""}"')
        if mode == 'follow':
            r += await _gz_service('/gui/follow/offset', 'gz.msgs.Vector3d', 'gz.msgs.Boolean',
                                   f'x: {offset_x}, y: 0, z: {offset_z}')
        return r
    if mode == 'robot_top':
        s = rosview.watcher().state().get('pose') or {}
        x, y = s.get('x', x), s.get('y', y)
        await _gz_service('/gui/follow', 'gz.msgs.StringMsg', 'gz.msgs.Boolean', 'data: ""')
    # camera x axis points down: pitch +90 deg
    return await _gz_service('/gui/move_to/pose', 'gz.msgs.GUICamera', 'gz.msgs.Boolean',
                             f'pose: {{position: {{x: {x}, y: {y}, z: {z}}}, '
                             f'orientation: {{w: 0.7071068, x: 0, y: 0.7071068, z: 0}}}}')


@mcp.tool()
async def gz_world(action: str = 'pause', steps: int = 1, force: bool = False):
    """Pause / play the simulation, or step it `steps` iterations while paused. action: pause|play|step.
    WARNING (seen 2026-10-20): Nav2's lifecycle bond runs on wall time, so a pause of more than ~4 s
    makes lifecycle_manager declare collision_monitor dead and shut Nav2 down - the run is then over.
    pause/step therefore need force=True; use it only to freeze a scene for screenshots, then restart."""
    if action in ('pause', 'step') and not force:
        return ('refused: pausing > ~4 s takes Nav2 down (lifecycle bond on wall time). For a still '
                'picture use screenshot / map_view instead; pass force=True if the run may end.')
    world = await _world()
    if not world:
        return 'no /world/*/control service found (is Gazebo running in our partition?)'
    req = {'pause': 'pause: true', 'play': 'pause: false', 'step': f'pause: true, multi_step: {int(steps)}'}[action]
    journal('gz_world', action=action, steps=steps)
    return await _gz_service(f'/world/{world}/control', 'gz.msgs.WorldControl', 'gz.msgs.Boolean', req)


# ---------------------------------------------------------------- windows
def _shot(target, raise_window, max_width):
    img, info, how = x11win.capture(target, raise_window)
    data, scale = x11win.encode(img, max_width)
    SCALE[info['id'] if info else 'desktop'] = scale
    path = os.path.join(run_dir(), f'shot_{re.sub(r"[^A-Za-z0-9]+", "_", str(target))}_{stamp()}.jpg')
    with open(path, 'wb') as f:
        f.write(data)
    desc = (f'{info["title"]!r} {info["w"]}x{info["h"]} at ({info["x"]},{info["y"]})' if info else 'whole screen')
    return data, scale, f'{desc}; via {how}; image scale {scale:.3f} (click coords = image pixels); saved {path}'


@mcp.tool()
def screenshot(target: str = 'gazebo', raise_window: bool = False, max_width: int = 1400):
    """Screenshot a window: 'gazebo', 'rviz', 'desktop', a title substring or a window id.
    Reads the window's own pixels (works while covered); raise_window=True brings it to the front first."""
    data, _, desc = _shot(target, raise_window, max_width)
    return [Image(data=data, format='jpeg'), desc]


def _tile(frames, max_width=1600, label_color=(255, 255, 0)):
    """frames: [(PIL image, label)] -> JPEG bytes of a grid (2 columns up to 4 frames, else 3)."""
    cols = 2 if len(frames) <= 4 else 3
    rows = (len(frames) + cols - 1) // cols
    tw = max_width // cols
    th = round(frames[0][0].height * tw / frames[0][0].width)
    sheet = PILImage.new('RGB', (tw * cols, th * rows), 'white')
    for k, (img, lab) in enumerate(frames):
        tile = img.convert('RGB').resize((tw, th), PILImage.LANCZOS)
        d = ImageDraw.Draw(tile)
        text = f'#{k + 1}  {lab}'
        # contrasting box: yellow on RViz's light toolbar was unreadable
        box = d.textbbox((8, 8), text)
        d.rectangle((box[0] - 4, box[1] - 3, box[2] + 4, box[3] + 3),
                    fill='white' if sum(label_color) < 300 else 'black')
        d.text((8, 8), text, fill=label_color)
        sheet.paste(tile, ((k % cols) * tw, (k // cols) * th))
    buf = io.BytesIO()
    sheet.save(buf, 'JPEG', quality=80)
    return buf.getvalue()


def _pick(seq, n=9):
    if len(seq) <= n:
        return list(seq)
    return [seq[round(i * (len(seq) - 1) / (n - 1))] for i in range(n)]


@mcp.tool()
async def screenshot_series(target: str = 'gazebo', count: int = 4, interval: float = 2.0, max_width: int = 1600):
    """`count` screenshots `interval` s apart, tiled into one image (each stamped with sim time) - to
    see motion, oscillation or a wedge."""
    count = max(2, min(count, 9))
    frames = []
    for i in range(count):
        img, info, _ = await anyio.to_thread.run_sync(x11win.capture, target, False)
        frames.append((img, f't={rosview.watcher().now():.1f}s'))
        if i < count - 1:
            await asyncio.sleep(interval)
    data = _tile(frames, max_width)
    path = os.path.join(run_dir(), f'series_{target}_{stamp()}.jpg')
    with open(path, 'wb') as f:
        f.write(data)
    return [Image(data=data, format='jpeg'), f'{count} frames, {interval}s apart; saved {path}']


@mcp.tool()
async def record_gif(target: str = 'gazebo', seconds: float = 10.0, fps: float = 4.0, width: int = 900):
    """Record a window as an animated GIF (window pixels, works while covered) into the run folder -
    for the user and the docs when a still does not show the behaviour (oscillation, wedge, U-turn).
    Returns a tiled sheet of 9 evenly spaced frames (Claude sees stills, not animation)."""
    n = max(2, min(int(seconds * fps), 240))
    frames, wall = [], []
    t_end = time.time() + seconds
    for i in range(n):
        t0 = time.time()
        if i and t0 >= t_end:
            break
        img, _, _ = await anyio.to_thread.run_sync(x11win.capture, target, False)
        wall.append(t0)
        s = width / img.width
        frames.append((img.resize((width, round(img.height * s)), PILImage.LANCZOS),
                       f't={rosview.watcher().now():.1f}s'))
        await asyncio.sleep(max(0.0, 1.0 / fps - (time.time() - t0)))
    # real frame spacing (capture can be slower than 1/fps in the server process), so the GIF
    # plays at real speed instead of fast-forwarding
    dur = [int(1000 * (b - a)) for a, b in zip(wall, wall[1:])]
    dur.append(dur[-1] if dur else int(1000 / fps))
    span = wall[-1] - wall[0] + dur[-1] / 1000
    path = os.path.join(run_dir(), f'gif_{re.sub(r"[^A-Za-z0-9]+", "_", target)}_{stamp()}.gif')
    pal = [f.convert('P', palette=PILImage.ADAPTIVE, colors=128) for f, _ in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=dur, loop=0, optimize=True)
    sheet = _tile(_pick(frames))
    return [Image(data=sheet, format='jpeg'),
            f'GIF {len(frames)} frames over {span:.1f} s wall ({len(frames) / span:.1f} fps real time), '
            f'{os.path.getsize(path) // 1024} KB: {path}']


@mcp.tool()
def map_gif(seconds: float = 60.0, frames: int = 15, radius: float = 0.0):
    """Animated top-down GIF of the last `seconds` of track on the map (fixed view; track grows,
    green forward / red reverse / orange spin) - shows how the robot moved through a spot, which no
    screenshot can. radius > 0: square of that half-size around the window's track; else whole map.
    Saved for the user/docs; returns a tiled sheet of the frames."""
    w = rosview.watcher()
    tr = w.track_array()
    with w.lock:
        m = w.map
    if m is None or len(tr['t']) < 2:
        return 'no map or track yet'
    t1 = tr['t'][-1]
    k0 = tr['t'] >= t1 - seconds
    base = dict(map=rosview._grid(m), map_res=m.info.resolution,
                map_origin=[m.info.origin.position.x, m.info.origin.position.y], cov=np.zeros((0, 4)))
    xs, ys = tr['x'][k0], tr['y'][k0]
    center = ((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2)
    r = radius or None
    if r is None and len(xs):
        r = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2 + 1.5
    imgs = []
    for tk in np.linspace(t1 - seconds, t1, max(2, min(frames, 60))):
        k = k0 & (tr['t'] <= tk)
        if k.sum() < 2:
            continue
        data = {**base, **{key: tr[key][k] for key in ('t', 'x', 'y', 'yaw', 'vx', 'wz')}}
        png = rosview.render(data=data, radius=r, center=center, width_px=640,
                             title_extra=f'  ({tk - t1:+.0f} s)')
        imgs.append((PILImage.open(io.BytesIO(png)).convert('RGB'), f't={tk:.0f}s'))
    path = os.path.join(run_dir(), f'mapgif_{stamp()}.gif')
    pal = [f.convert('P', palette=PILImage.ADAPTIVE, colors=64) for f, _ in imgs]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=400, loop=0, optimize=True)
    return [Image(data=_tile(_pick(imgs), 1500, (200, 0, 0)), format='jpeg'),
            f'map GIF {len(imgs)} frames: {path}']


@mcp.tool()
def list_windows():
    """All top-level windows (id, title, geometry, visible)."""
    return jdump([{**w, 'id': hex(w['id'])} for w in x11win.list_windows()])


def _win_xy(target, x, y, image_coords):
    info = x11win.find(target)
    if info is None:
        raise ValueError('input needs a window target, not the desktop')
    s = SCALE.get(info['id'], 1.0) if image_coords else 1.0
    return info, x / s, y / s


@mcp.tool()
def click(target: str, x: float, y: float, button: str = 'left', count: int = 1, image_coords: bool = True):
    """Click in a window (raises it; moves the real mouse). x, y are pixels in the last screenshot of
    that window (image_coords=True) or raw window pixels. button: left|middle|right; count=2 double-clicks."""
    info, wx, wy = _win_xy(target, x, y, image_coords)
    x11win.click(info, wx, wy, button, count)
    return f'clicked {button} x{count} at window ({wx:.0f},{wy:.0f}) of {info["title"]!r}'


@mcp.tool()
def drag(target: str, x1: float, y1: float, x2: float, y2: float, button: str = 'left',
         modifiers: str = '', image_coords: bool = True):
    """Drag in a window, e.g. orbit/pan the Gazebo or RViz view (RViz: left = rotate, middle = pan,
    right = zoom; Gazebo: left = pan, right... see its help). modifiers: '+'-joined keys held, e.g. 'shift'."""
    info, a, b = _win_xy(target, x1, y1, image_coords)
    _, c, d = _win_xy(target, x2, y2, image_coords)
    x11win.drag(info, a, b, c, d, button, modifiers=[m for m in modifiers.split('+') if m])
    return f'dragged {button} ({a:.0f},{b:.0f})->({c:.0f},{d:.0f}) in {info["title"]!r}'


@mcp.tool()
def scroll(target: str, x: float, y: float, clicks: int = 3, image_coords: bool = True):
    """Mouse-wheel at a point (positive = up/zoom in, negative = down/zoom out)."""
    info, wx, wy = _win_xy(target, x, y, image_coords)
    x11win.scroll(info, wx, wy, clicks)
    return f'scrolled {clicks} at ({wx:.0f},{wy:.0f}) in {info["title"]!r}'


@mcp.tool()
def key(target: str, combo: str):
    """Press a key combination in a window, e.g. 'ctrl+s', 'Escape', 'Return', 'g'."""
    info = x11win.find(target)
    x11win.key_combo(info, combo)
    return f'pressed {combo} in {info["title"]!r}'


@mcp.tool()
def type_text(target: str, text: str):
    """Type text into the focused field of a window (click the field first)."""
    info = x11win.find(target)
    x11win.type_text(info, text)
    return f'typed {len(text)} chars into {info["title"]!r}'


@mcp.tool()
def record_video(target: str = 'gazebo', seconds: float = 20.0, fps: int = 10):
    """Record an MP4 of a window (raised to the front) into the run folder, in the background - for
    the user / the report (Claude cannot watch it; use screenshot_series instead)."""
    info = x11win.find(target)
    if info is not None:
        x11win.activate(info)
        x, y, w, h = info['x'], info['y'], info['w'] // 2 * 2, info['h'] // 2 * 2
    else:
        x, y, w, h = 0, 0, 1920, 1080
    path = os.path.join(run_dir(), f'video_{re.sub(r"[^A-Za-z0-9]+", "_", target)}_{stamp()}.mp4')
    subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'x11grab', '-framerate', str(fps),
                      '-video_size', f'{w}x{h}', '-i', f'{os.environ.get("DISPLAY", ":1")}+{x},{y}',
                      '-t', str(seconds), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', path],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return f'recording {seconds}s to {path}'


if __name__ == '__main__':
    os.makedirs(RUNS, exist_ok=True)
    rosview.watcher()
    mcp.run()
