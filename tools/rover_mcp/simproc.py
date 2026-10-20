"""Start and stop sim launches in the isolated env (simenv.sh) and clean up stale sim processes.

Cleanup finds processes by the GZ_PARTITION in their environment, not by `pkill -f` patterns (those
also matched the shell running them, exit 144, in earlier sessions). Shells, editors and this
process's own ancestors are never touched.
"""
import os
import signal
import subprocess
import time

PARTITION = os.environ.get('GZ_PARTITION', 'rover_mcp')
SHELLS = {'bash', 'sh', 'zsh', 'fish', 'dash', 'code', 'node', 'claude', 'tmux', 'screen'}


def _ancestors():
    pids, p = set(), os.getpid()
    while p > 1:
        pids.add(p)
        try:
            with open(f'/proc/{p}/stat') as f:
                p = int(f.read().rsplit(')', 1)[1].split()[1])
        except Exception:
            break
    return pids


def partition_pids(exclude=()):
    """Sim processes in our GZ partition (stale ones too, or a sim started by hand after sourcing
    simenv.sh). exclude: extra PIDs to leave alone (e.g. an experiment runner)."""
    skip, out = _ancestors() | set(exclude), []
    for p in os.listdir('/proc'):
        if not p.isdigit() or int(p) in skip:
            continue
        try:
            with open(f'/proc/{p}/comm') as f:
                comm = f.read().strip()
            if comm in SHELLS or comm.startswith('python') and 'rover_mcp' in cmdline(int(p)):
                continue
            with open(f'/proc/{p}/environ', 'rb') as f:
                env = f.read().split(b'\0')
        except Exception:
            continue
        if f'GZ_PARTITION={PARTITION}'.encode() in env:
            out.append(int(p))
    return out


def cmdline(pid):
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            return f.read().replace(b'\0', b' ').decode(errors='replace').strip()
    except Exception:
        return '?'


def start(argv, log_path):
    log = open(log_path, 'w')
    p = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         start_new_session=True, env=os.environ.copy())
    p._rover_log = log
    return p


def stop(p, grace=12.0, exclude=()):
    """SIGINT the launch's process group, then SIGKILL it and anything left in our partition."""
    if p is not None and p.poll() is None:
        try:
            os.killpg(p.pid, signal.SIGINT)
            p.wait(grace)
        except Exception:
            pass
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            pass
    for pid in partition_pids(exclude):
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
    if p is not None and getattr(p, '_rover_log', None):
        p._rover_log.close()
    time.sleep(1.0)
