"""
Fake robot for testing without hardware: a simulated ESP32 (firmware/explorer_esp32 protocol)
and a simulated YDLIDAR X2 (real packet format) in a small 2-D world, served on TCP ports.
Point the real nodes at it with pyserial socket:// URLs:

    ros2 run explorer_bringup fake_robot                      # ESP32 on :47001, X2 on :47002
    ros2 launch explorer_bringup robot.launch.py esp_port:=socket://localhost:47001 \
        lidar_port:=socket://localhost:47002
    ros2 launch explorer_exploration bringup.launch.py sim:=false rviz:=true \
        esp_port:=socket://localhost:47001 lidar_port:=socket://localhost:47002

The robot follows S commands (first-order lag, skid-steer with the effective track), stops
0.5 s after the last one like the firmware's watchdog, and its gyro/accel are given in the
IMU chip's axes as mounted in the URDF (rolled 180 deg: yaw rate on -z, gravity -9.81 on z).
The X2 is ray-cast against the world's walls from the URDF's LiDAR position, clockwise,
with the X2's angle correction undone, so x2_lidar has to decode it exactly as the real one.
--slip makes the left rear wheel spin 50 % fast; --no-imu reports no IMU data.
"""

import argparse
import math
import random
import selectors
import socket
import struct
import time

from explorer_bringup.esp32_bridge import checksum

LIDAR_X = 0.079                             # laser_frame ahead of base_footprint (URDF)
# World walls (m): a 9 x 6 m room, a wall with a doorway, a box, a pillar. Robot starts at 0,0.
WORLD = [((-1.0, -2.0), (8.0, -2.0)), ((8.0, -2.0), (8.0, 4.0)), ((8.0, 4.0), (-1.0, 4.0)),
         ((-1.0, 4.0), (-1.0, -2.0)),
         ((3.5, -2.0), (3.5, 0.8)), ((3.5, 2.0), (3.5, 4.0)),
         ((5.5, 1.0), (6.2, 1.0)), ((6.2, 1.0), (6.2, 1.6)), ((6.2, 1.6), (5.5, 1.6)),
         ((5.5, 1.6), (5.5, 1.0)),
         ((1.5, 2.5), (1.8, 2.5)), ((1.8, 2.5), (1.8, 2.8)), ((1.8, 2.8), (1.5, 2.8)),
         ((1.5, 2.8), (1.5, 2.5))]


def raycast(x, y, angle, max_range=8.0):
    """Distance (m) from (x, y) along angle to the nearest wall, or None beyond max_range."""
    dx, dy = math.cos(angle), math.sin(angle)
    best = None
    for (ax, ay), (bx, by) in WORLD:
        ex, ey = bx - ax, by - ay
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((ax - x) * ey - (ay - y) * ex) / den
        u = ((ax - x) * dy - (ay - y) * dx) / den
        if t > 0 and 0 <= u <= 1 and (best is None or t < best):
            best = t
    return best if best is not None and best <= max_range else None


def x2_correction(dist_mm):
    return math.degrees(math.atan(21.8 * (155.3 - dist_mm) / (155.3 * dist_mm))) if dist_mm else 0.0


def x2_packet(ct, raw_angles, dists_mm):
    """One X2 packet; raw_angles are what the X2 reports before its angle correction."""
    fsa = int(round(raw_angles[0] % 360 * 64)) << 1 | 1
    lsa = int(round(raw_angles[-1] % 360 * 64)) << 1 | 1
    si = [min(int(d * 4), 0xFFFF) for d in dists_mm]
    cs = 0x55AA ^ (len(si) << 8 | ct) ^ fsa ^ lsa
    for v in si:
        cs ^= v
    return (b'\xaa\x55' + struct.pack('<BBHHH', ct, len(si), fsa, lsa, cs)
            + struct.pack(f'<{len(si)}H', *si))


class Port:
    """A TCP server that holds one client at a time (like one program opening a serial port)."""

    def __init__(self, sel, port, name):
        self.name, self.client = name, None
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.srv.bind(('127.0.0.1', port))
        except OSError as e:
            raise SystemExit(f'fake_robot: port {port} is taken ({e.strerror}): another fake_robot '
                             'is still running (stop it), or choose --esp-port/--lidar-port')
        self.srv.listen(1)
        self.srv.setblocking(False)
        sel.register(self.srv, selectors.EVENT_READ, self)
        self.sel = sel
        print(f'fake_robot: {name} on socket://localhost:{port}', flush=True)

    def accept(self):
        conn, _ = self.srv.accept()
        if self.client:
            self.drop()
        conn.setblocking(False)
        self.client = conn
        print(f'fake_robot: {self.name} connected', flush=True)
        return conn

    def send(self, data):
        if self.client:
            try:
                self.client.sendall(data)
            except OSError:
                self.drop()

    def recv(self):
        if not self.client:
            return b''
        try:
            data = self.client.recv(4096)
        except BlockingIOError:
            return b''
        except OSError:
            data = b''
        if not data:
            self.drop()
        return data

    def drop(self):
        print(f'fake_robot: {self.name} disconnected', flush=True)
        self.client.close()
        self.client = None


class FakeRobot:
    def __init__(self, args):
        self.args = args
        self.sel = selectors.DefaultSelector()
        self.esp = Port(self.sel, args.esp_port, 'ESP32')
        self.x2 = Port(self.sel, args.lidar_port, 'X2')
        self.target = [0.0, 0.0]
        self.speed = [0.0, 0.0]
        self.travel = [0.0] * 4
        self.x = self.y = self.th = 0.0
        self.last_cmd = 0.0
        self.watchdog = False
        self.buf = b''
        self.ms0 = time.monotonic()

    def command(self, line):
        body, star, cs = line.partition('*')
        if star and int(cs, 16) != checksum(body):
            self.esp.send(b'# ERR checksum\n')
            return
        parts = body.split(',')
        if parts[0] == 'S' and len(parts) == 3:
            self.target = [max(-0.5, min(0.5, float(v))) for v in parts[1:]]
            self.last_cmd, self.watchdog = time.monotonic(), False
        elif body == 'G':
            self.esp.send(b'# gyro bias 0.000 0.000 0.000 deg/s\n')

    def step_esp(self, dt):
        *lines, self.buf = (self.buf + self.esp.recv()).split(b'\n')
        for raw in lines:
            self.command(raw.decode(errors='replace').strip())
        if any(self.target) and time.monotonic() - self.last_cmd > 0.5:
            self.target, self.watchdog = [0.0, 0.0], True
        a = min(1.0, dt / 0.1)                  # motor lag, tau 0.1 s
        for s in range(2):
            self.speed[s] += a * (self.target[s] - self.speed[s])
        vl, vr = self.speed
        v, w = (vl + vr) / 2, (vr - vl) / self.args.track
        self.x += v * dt * math.cos(self.th + w * dt / 2)
        self.y += v * dt * math.sin(self.th + w * dt / 2)
        self.th += w * dt
        for i in range(4):
            self.travel[i] += self.speed[0 if i < 2 else 1] * dt * (1.5 if self.args.slip and i == 1 else 1.0)
        n = lambda sd: random.gauss(0.0, sd)
        um = [round(t * 1e6) for t in self.travel]
        flags = (0 if self.args.no_imu else 1) | 2 | (4 if self.watchdog else 0)
        g = (0.0, 0.0, 0.0) if self.args.no_imu else (n(0.002), n(0.002), -w + n(0.002))
        acc = (0.0, 0.0, 0.0) if self.args.no_imu else (n(0.02), n(0.02), -9.807 + n(0.02))
        pwm = [int(400 * s) for s in self.speed]
        body = (f'T,{int((time.monotonic() - self.ms0) * 1000)},{um[0]},{um[1]},{um[2]},{um[3]},'
                f'{g[0]:.5f},{g[1]:.5f},{g[2]:.5f},{acc[0]:.3f},{acc[1]:.3f},{acc[2]:.3f},'
                f'{pwm[0]},{pwm[1]},{flags}')
        self.esp.send(f'{body}*{checksum(body):02X}\n'.encode())

    def turn_x2(self):
        lx = self.x + LIDAR_X * math.cos(self.th)
        ly = self.y + LIDAR_X * math.sin(self.th)
        out = [x2_packet(0x01 | 70 << 1, [0.0], [0.0])]          # start of turn
        n = 430
        for p0 in range(0, n, 40):
            # The X2 samples at evenly spaced raw angles (clockwise); each distance lies at
            # raw angle + the X2's correction for that distance (found by fixed-point steps)
            raw = [k * 360.0 / n for k in range(p0, min(p0 + 40, n))]
            dists = []
            for a in raw:
                d = 0.0
                for _ in range(3):
                    r = raycast(lx, ly, self.th - math.radians(a + x2_correction(d)))
                    d = 0.0 if r is None or r < 0.12 else r * 1000
                dists.append(d + random.gauss(0, 5) if d else 0.0)
            out.append(x2_packet(0, raw, dists))
        self.x2.send(b''.join(out))

    def run(self):
        print('fake_robot: Ctrl-C to stop', flush=True)
        self.esp.send(b'# explorer_esp32 starting - keep the robot still\n# ready\n')
        next_esp = next_x2 = last = time.monotonic()
        while True:
            for key, _ in self.sel.select(timeout=0.002):
                if key.data.accept() and key.data is self.esp:
                    self.esp.send(b'# explorer_esp32 starting - keep the robot still\n# ready\n')
            now = time.monotonic()
            if now >= next_esp:
                self.step_esp(now - last)
                last, next_esp = now, next_esp + 0.02
            if now >= next_x2:
                self.turn_x2()
                next_x2 += 1 / 7.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--esp-port', type=int, default=47001)
    ap.add_argument('--lidar-port', type=int, default=47002)
    ap.add_argument('--track', type=float, default=0.43, help='effective track of the fake robot (m)')
    ap.add_argument('--slip', action='store_true', help='left rear wheel spins 50 %% fast')
    ap.add_argument('--no-imu', action='store_true', help='report no IMU data')
    try:
        FakeRobot(ap.parse_known_args()[0]).run()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
