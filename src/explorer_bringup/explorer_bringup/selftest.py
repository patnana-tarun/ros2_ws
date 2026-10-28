"""
Self-test of the real-robot software without hardware. Prints PASS / FAIL / SKIP per check;
exit code 0 when nothing failed.

    ros2 run explorer_bringup hw_selftest              # unit checks + fake robot (~40 s)
    ros2 run explorer_bringup hw_selftest --slam       # + SLAM Toolbox builds a map (~70 s)
    ros2 run explorer_bringup hw_selftest --firmware   # + compile the ESP32 firmware (arduino-cli)
    ros2 run explorer_bringup hw_selftest --all

Runs in its own ROS domain on localhost and free TCP ports, so a running robot, sim or
fake_robot is not disturbed. Logs of the started processes: /tmp/hw_selftest_*.log
"""

import argparse
import math
import os
import random
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time

from ament_index_python.packages import get_package_share_directory

RESULTS = []


def report(name, ok, detail=''):
    tag = {True: 'PASS', False: 'FAIL', None: 'SKIP'}[ok]
    RESULTS.append(ok)
    print(f'[{tag}] {name}' + (f' - {detail}' if detail else ''), flush=True)


def isolate_env():
    """Own ROS domain, localhost only, no discovery server (set before rclpy starts)."""
    for k in ('ROS_DISCOVERY_SERVER', 'ROS_SUPER_CLIENT', 'FASTRTPS_DEFAULT_PROFILES_FILE',
              'ROS_LOCALHOST_ONLY', 'ROS_STATIC_PEERS'):
        os.environ.pop(k, None)
    os.environ['ROS_DOMAIN_ID'] = str(random.randint(150, 230))
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class Proc:
    """A child process in its own process group, so stopping it stops everything it started."""

    def __init__(self, name, cmd):
        self.log = f'/tmp/hw_selftest_{name}.log'
        self.p = subprocess.Popen(cmd, stdout=open(self.log, 'w'), stderr=subprocess.STDOUT,
                                  start_new_session=True)

    def stop(self):
        for sig, wait in ((signal.SIGINT, 8), (signal.SIGKILL, 2)):
            if self.p.poll() is not None:
                return
            try:
                os.killpg(self.p.pid, sig)
                self.p.wait(wait)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass


# ---------------------------------------------------------------- unit checks (no ROS graph)
def unit_checks(share):
    import rclpy
    from explorer_bringup.esp32_bridge import Esp32Bridge, checksum
    from explorer_bringup.fake_robot import x2_correction, x2_packet
    from explorer_bringup.x2_lidar import parse

    # 1. The firmware's own T-line format string, as the bridge reads it
    ino = os.path.join(share, 'firmware', 'explorer_esp32', 'explorer_esp32.ino')
    fmt = re.search(r'pilink::send\("([^"]+)"', open(ino).read()).group(1)
    pyfmt = re.sub(r'%l?[ud]', '%d', fmt)
    vals = (1234, 100000, 101000, -50000, -51000, 0.01, -0.02, 0.5, 0.1, 0.2, -9.8, 120, -80, 3)
    body = pyfmt % vals
    rclpy.init(args=['--ros-args', '-p', 'mock:=true'])
    bridge = Esp32Bridge()
    got, odom = [], []
    bridge.telemetry = lambda *a: got.append(a)
    bridge.on_line(f'{body}*{checksum(body):02X}')
    bridge.on_line(f'{body}*{(checksum(body) + 1) % 256:02X}')          # bad checksum
    ok = (len(got) == 1 and got[0][0] == 1234 and abs(got[0][1][0] - 0.1) < 1e-9
          and abs(got[0][2][2] - 0.5) < 1e-9 and bridge.flags == 3)
    report('firmware T-line format matches the bridge parser', ok, f'"{fmt[:40]}..."')

    # 2. Slip detection: left rear 50 % faster than left front
    del bridge.telemetry
    bridge.publish_odom = lambda stamp, vx, wz, slip: odom.append((vx, slip))
    bridge.publish_imu = lambda *a: None
    for ms, d in ((0, (0, 0, 0, 0)), (20, (4000, 4000, 4000, 4000)), (40, (8000, 10000, 8000, 8000))):
        b = f'T,{ms},{d[0]},{d[1]},{d[2]},{d[3]},0,0,0,0,0,-9.8,0,0,3'
        bridge.on_line(f'{b}*{checksum(b):02X}')
    odom = [(round(v, 3), s) for v, s in odom]
    report('slip check flags a slipping wheel', odom == [(0.2, False), (0.225, True)], str(odom))
    bridge.destroy_node()
    rclpy.shutdown()

    # 3. X2 packets: decode in random chunks, with garbage and a truncated packet in between
    random.seed(7)
    stream, expect = b'', []
    for p in range(30):
        raw = [p * 12 + k * 0.3 for k in range(40)]
        dist = [random.choice([0.0, random.uniform(150, 7900)]) for _ in raw]
        pk = x2_packet(1 if p % 10 == 0 else 0, raw, dist)
        expect.append([(a + x2_correction(d), d) for a, d in zip(raw, dist)])
        stream += (b'\x13\xaa\x55\x07' + pk[:-5] if p % 7 == 3 else b'') + pk
    buf, out, i = b'', [], 0
    while i < len(stream):
        n = random.randint(1, 200)
        pk, buf = parse(buf + stream[i:i + n])
        out += pk
        i += n
    err = max((abs(a - ea) for (_, pts), e in zip(out, expect) for (a, _), (ea, _) in zip(pts, e)),
              default=99)
    report('X2 packet decoding (chunks, garbage, angle correction)',
           len(out) == 30 and sum(s for s, _ in out) == 3 and err < 0.05,
           f'{len(out)}/30 packets, max angle error {err:.3f} deg')


# ---------------------------------------------------------------- fake robot checks
def fake_robot_checks(slam):
    import rclpy
    from geometry_msgs.msg import TwistStamped
    from nav_msgs.msg import OccupancyGrid, Odometry
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.qos import DurabilityPolicy, QoSProfile
    from sensor_msgs.msg import Imu, JointState, LaserScan
    from tf2_ros import Buffer, TransformListener
    from explorer_bringup.fake_robot import LIDAR_X, raycast

    pe, pl = free_port(), free_port()
    procs = [Proc('fake_robot', ['ros2', 'run', 'explorer_bringup', 'fake_robot',
                                 '--esp-port', str(pe), '--lidar-port', str(pl)])]
    time.sleep(1.0)
    # --slam starts mapping.launch.py (robot.launch.py + SLAM Toolbox), else robot.launch.py
    procs.append(Proc('robot_launch', ['ros2', 'launch', 'explorer_bringup',
                                       'mapping.launch.py' if slam else 'robot.launch.py',
                                       f'esp_port:=socket://localhost:{pe}',
                                       f'lidar_port:=socket://localhost:{pl}']))
    rclpy.init()
    node = rclpy.create_node('hw_selftest')
    msgs = {t: [] for t in ('/wheel/odom', '/imu', '/joint_states', '/odom', '/scan', '/map')}
    for topic, typ in (('/wheel/odom', Odometry), ('/imu', Imu), ('/joint_states', JointState),
                       ('/odom', Odometry), ('/scan', LaserScan)):
        node.create_subscription(typ, topic, lambda m, t=topic: msgs[t].append((time.time(), m)), 50)
    node.create_subscription(OccupancyGrid, '/map', lambda m: msgs['/map'].append((time.time(), m)),
                             QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    cmd = node.create_publisher(TwistStamped, '/cmd_vel', 10)
    tf = Buffer()
    TransformListener(tf, node)
    ex = SingleThreadedExecutor()
    ex.add_node(node)
    threading.Thread(target=ex.spin, daemon=True).start()

    def rate(topic, secs=3.0):
        t0 = time.time()
        time.sleep(secs)
        return sum(1 for t, _ in msgs[topic] if t >= t0) / secs

    def drive(v, w, secs):
        end = time.time() + secs
        while time.time() < end:
            m = TwistStamped()
            m.header.stamp = node.get_clock().now().to_msg()
            m.twist.linear.x, m.twist.angular.z = v, w
            cmd.publish(m)
            time.sleep(0.05)

    try:
        t0 = time.time()
        while time.time() - t0 < 20 and not (msgs['/odom'] and msgs['/scan']):
            time.sleep(0.5)
        report(f"{'mapping' if slam else 'robot'}.launch.py comes up on the fake robot", bool(msgs['/odom'] and msgs['/scan']),
               f'after {time.time() - t0:.0f} s (logs /tmp/hw_selftest_*.log)')
        if not msgs['/odom']:
            return
        for topic, lo, hi in (('/wheel/odom', 40, 60), ('/imu', 40, 60), ('/joint_states', 40, 60),
                              ('/odom', 25, 35), ('/scan', 6, 8)):
            r = rate(topic, 2.0)
            report(f'{topic} rate', lo <= r <= hi, f'{r:.1f} Hz (expected {lo}-{hi})')

        imu = msgs['/imu'][-1][1]
        report('/imu frame and gravity', imu.header.frame_id == 'imu_link'
               and abs(imu.linear_acceleration.z + 9.81) < 0.2,
               f'{imu.header.frame_id}, z {imu.linear_acceleration.z:.2f} m/s2 (chip facing down)')

        scan = msgs['/scan'][-1][1]
        bad = []
        for deg in (0, 45, 90, -90, 180):
            exp = raycast(LIDAR_X, 0.0, math.radians(deg))
            k = int(round((math.radians(deg) - scan.angle_min) / scan.angle_increment)) % len(scan.ranges)
            near = [scan.ranges[(k + j) % len(scan.ranges)] for j in (-1, 0, 1)]
            got = sorted(near)[1]
            if exp is None or abs(got - exp) > 0.08:
                bad.append(f'{deg} deg: {got:.2f} vs {exp}')
        report('/scan geometry against the fake world', len(scan.ranges) == 360 and not bad,
               '; '.join(bad) or '0/45/90/-90/180 deg within 8 cm')

        try:
            tf.lookup_transform('odom', 'laser_frame', rclpy.time.Time())
            report('TF odom -> base_footprint -> laser_frame', True)
        except Exception as e:                      # noqa: BLE001 - any TF error is a failure
            report('TF odom -> base_footprint -> laser_frame', False, str(e)[:80])

        drive(0.15, 0.3, 3.0)
        tw = msgs['/odom'][-1][1].twist.twist
        report('EKF follows a command (0.15 m/s, 0.30 rad/s)',
               abs(tw.linear.x - 0.15) < 0.03 and abs(tw.angular.z - 0.3) < 0.06,
               f'vx {tw.linear.x:.3f}, wz {tw.angular.z:.3f}')
        time.sleep(1.5)
        vx = msgs['/wheel/odom'][-1][1].twist.twist.linear.x
        report('robot stops when /cmd_vel stops', abs(vx) < 0.02, f'wheel vx {vx:.3f} after 1.5 s')

        if slam:
            drive(0.0, 0.5, 8.0)                    # turn on the spot
            drive(0.15, 0.0, 6.0)                   # then drive ahead
            time.sleep(4)
            ok = bool(msgs['/map'])
            detail = 'no /map'
            if ok:
                g = msgs['/map'][-1][1]
                occ = sum(1 for v in g.data if v > 50)
                ok = occ > 100
                detail = (f'{g.info.width} x {g.info.height} cells at {g.info.resolution:.2f} m, '
                          f'{occ} occupied')
            report('mapping.launch.py: SLAM Toolbox maps the fake world', ok, detail)
    finally:
        ex.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()
        for p in reversed(procs):
            p.stop()


def firmware_check(share):
    cli = shutil.which('arduino-cli')
    if not cli:
        report('ESP32 firmware compiles', None, 'arduino-cli not installed')
        return
    src = os.path.join(share, 'firmware', 'explorer_esp32')
    r = subprocess.run([cli, 'compile', '--fqbn', 'esp32:esp32:esp32', '--warnings', 'all',
                        '--build-path', '/tmp/hw_selftest_fw_build', src],
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    size = re.search(r'Sketch uses (\d+) bytes', out)
    warn = len(re.findall(r'warning:', out))
    report('ESP32 firmware compiles', r.returncode == 0 and warn == 0,
           f'{int(size.group(1)) // 1024} kB, {warn} warnings' if size else out.strip()[-200:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--slam', action='store_true', help='also run SLAM Toolbox on the fake robot')
    ap.add_argument('--firmware', action='store_true', help='also compile the ESP32 firmware')
    ap.add_argument('--all', action='store_true')
    a, _ = ap.parse_known_args()
    isolate_env()
    share = get_package_share_directory('explorer_bringup')
    print(f'hw_selftest: ROS_DOMAIN_ID {os.environ["ROS_DOMAIN_ID"]}, localhost only', flush=True)
    unit_checks(share)
    fake_robot_checks(a.slam or a.all)
    if a.firmware or a.all:
        firmware_check(share)
    failed = RESULTS.count(False)
    print(f'\nhw_selftest: {RESULTS.count(True)} passed, {failed} failed, {RESULTS.count(None)} skipped')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
