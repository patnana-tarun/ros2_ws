"""
Hardware checks without ROS: read the ESP32 or the X2 directly and print what arrives.
Stop the robot launch first (only one program can hold a serial port).

    ros2 run explorer_bringup esp32_check /dev/ttyUSB0                  # watch telemetry
    ros2 run explorer_bringup esp32_check /dev/ttyUSB0 --drive 0.1 0.1  # also run each side at 0.1 m/s
    ros2 run explorer_bringup x2_check /dev/ttyUSB1                     # watch the LiDAR

Ports may be pyserial URLs too (socket://localhost:47001 for fake_robot).
"""

import argparse
import math
import time

import serial

from explorer_bringup.esp32_bridge import IMU_OK, DRIVE_OK, WATCHDOG, checksum, with_checksum
from explorer_bringup.x2_lidar import parse


def open_port(url, baud, dtr=False):
    """Open a port, or exit with a hint. DTR/RTS low by default: the ESP32 keeps running."""
    try:
        ser = serial.serial_for_url(url, baud, timeout=0, do_not_open=True)
        ser.dtr, ser.rts = dtr, False
        ser.open()
    except (serial.SerialException, OSError, ValueError) as e:
        raise SystemExit(f'cannot open {url}: {e}\n'
                         'list ports: ls -l /dev/serial/by-path/ /dev/ttyUSB* /dev/ttyACM*; '
                         'busy? stop robot.launch.py / the Serial Monitor; denied? sudo usermod -aG dialout $USER')
    return ser


def esp32_check():
    ap = argparse.ArgumentParser(description='Watch the ESP32 telemetry (no ROS).')
    ap.add_argument('port')
    ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--drive', nargs=2, type=float, metavar=('LEFT', 'RIGHT'),
                    help='send S,<left>,<right> (m/s) at 10 Hz while running (wheels off the ground!)')
    ap.add_argument('--seconds', type=float, default=0, help='stop after this long (0 = Ctrl-C)')
    a = ap.parse_args()
    ser = open_port(a.port, a.baud)
    print(f'reading {a.port}; Ctrl-C to stop (sends S,0,0 on exit)')
    buf, lines, bad, other, prev, last_print, last_cmd = b'', 0, 0, 0, None, time.time(), 0.0
    t_end = time.time() + a.seconds if a.seconds else math.inf
    try:
        while time.time() < t_end:
            if a.drive and time.time() - last_cmd > 0.1:
                ser.write(with_checksum(f'S,{a.drive[0]:.3f},{a.drive[1]:.3f}').encode())
                last_cmd = time.time()
            buf += ser.read(4096)
            *raw, buf = buf.split(b'\n')
            for r in raw:
                line = r.decode('ascii', errors='replace').strip()
                if line.startswith('#'):
                    print('ESP32 says:', line[1:].strip())
                    continue
                body, star, cs = line.partition('*')
                if not body.startswith('T,'):
                    other += 1
                    continue
                if not star or int(cs, 16) != checksum(body):
                    bad += 1
                    continue
                lines += 1
                f = body.split(',')
                cur = (int(f[1]), [int(v) * 1e-6 for v in f[2:6]], [float(v) for v in f[6:12]],
                       int(f[12]), int(f[13]), int(f[14]))
                if prev is None:
                    prev = cur
                if time.time() - last_print >= 0.5 and cur[0] > prev[0]:
                    dt = (cur[0] - prev[0]) / 1000
                    v = [(c - p) / dt for c, p in zip(cur[1], prev[1])]
                    g, acc, flags = cur[2][:3], cur[2][3:], cur[5]
                    print(f'{lines / (time.time() - last_print):5.1f} lines/s  bad {bad}  '
                          f'| wheel m/s LF {v[0]:+.3f} LR {v[1]:+.3f} RF {v[2]:+.3f} RR {v[3]:+.3f} '
                          f'| pwm L {cur[3]:+4d} R {cur[4]:+4d} '
                          f'| gyro z {g[2]:+.3f} rad/s |acc| {math.dist(acc, (0, 0, 0)):.2f} m/s2 '
                          f'| {"IMU" if flags & IMU_OK else "NO-IMU"} '
                          f'{"drive" if flags & DRIVE_OK else "DRIVE-OFF"}'
                          f'{" WATCHDOG" if flags & WATCHDOG else ""}', flush=True)
                    prev, lines, last_print = cur, 0, time.time()
            if time.time() - last_print > 3:
                print(f'nothing valid for 3 s ({other} other lines, {bad} bad): wrong port, '
                      'firmware not flashed, or wrong baud', flush=True)
                last_print = time.time()
            time.sleep(0.005)
    except KeyboardInterrupt:
        pass
    finally:
        ser.write(with_checksum('S,0,0').encode())
        ser.close()


def x2_check():
    ap = argparse.ArgumentParser(description='Watch the YDLIDAR X2 (no ROS).')
    ap.add_argument('port')
    ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--no-dtr', action='store_true', help='leave DTR low (motor switch the other way)')
    ap.add_argument('--seconds', type=float, default=0, help='stop after this long (0 = Ctrl-C)')
    a = ap.parse_args()
    ser = open_port(a.port, a.baud, dtr=not a.no_dtr)
    print(f'reading {a.port}; Ctrl-C to stop. Angles are the X2\'s own: clockwise, 0 = its zero mark')
    buf, nbytes, packets, turns, points, last_turn, last = b'', 0, 0, 0, [], [], time.time()
    t_end = time.time() + a.seconds if a.seconds else math.inf
    try:
        while time.time() < t_end:
            chunk = ser.read(4096)
            nbytes += len(chunk)
            pk, buf = parse(buf + chunk)
            for start, pts in pk:
                packets += 1
                if start:
                    turns += 1
                    if len(points) > 50:
                        last_turn = points
                    points = []
                points += pts
            if time.time() - last >= 1.0:
                dt = time.time() - last
                msg = f'{nbytes / dt:6.0f} B/s  {packets / dt:5.1f} packets/s  {turns / dt:4.1f} turns/s'
                if turns and last_turn:
                    valid = [(ang % 360, d) for ang, d in last_turn if d > 0]
                    near = min(valid, key=lambda p: p[1]) if valid else None

                    def at(deg):
                        c = [d for ang, d in valid if abs((ang - deg + 180) % 360 - 180) < 3]
                        return f'{min(c) / 1000:.2f}' if c else '  - '
                    msg += (f'  | {len(last_turn)} points/turn, {len(valid)} valid | m at 0/90/180/270 deg: '
                            f'{at(0)} {at(90)} {at(180)} {at(270)}')
                    if near:
                        msg += f' | nearest {near[1] / 1000:.2f} m at {near[0]:.0f} deg'
                elif nbytes == 0:
                    msg += '  | no bytes: wrong port, no power, or motor off (try --no-dtr)'
                elif packets == 0:
                    msg += '  | bytes but no valid packets: wrong baud or not an X2'
                print(msg, flush=True)
                nbytes = packets = turns = 0
                last = time.time()
            time.sleep(0.005)
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
