---
tags: [concept]
source: src/explorer_bringup/firmware/explorer_esp32/pilink.h
---
# Serial protocol

Between the ESP32 ([[ESP32 firmware]]) and the Pi ([[esp32_bridge]]): USB serial, 115200
baud, 8N1, one ASCII line per message ending in `\n`. Readable in any serial monitor.

## Checksum
A line may end in `*HH`: two hex digits, the XOR of every character before the `*` (as in
NMEA GPS sentences). Both sides check it when present and drop the line if it is wrong; the
ESP32 answers `# ERR checksum`. Everything the ESP32 and the bridge send carries one; bench
keys typed by hand don't need one.

Example: `S,0.100,0.100*53` — XOR of `S,0.100,0.100` is 0x53. Python: `functools.reduce(lambda a, c: a ^ ord(c), text, 0)`.

## ESP32 → Pi
**`T` telemetry, every 20 ms (50 Hz):**
```
T,<ms>,<lf>,<lr>,<rf>,<rr>,<gx>,<gy>,<gz>,<ax>,<ay>,<az>,<pwmL>,<pwmR>,<flags>*HH
T,51234,152000,151480,149800,150120,0.00012,-0.00031,0.29871,0.041,-0.022,-9.803,96,103,3*49
```
| Field | Unit | Meaning |
|-------|------|---------|
| `ms` | ms | ESP32 time since boot; the bridge uses its differences as dt |
| `lf lr rf rr` | µm | total travel of left front, left rear, right front, right rear since boot (signed) |
| `gx gy gz` | rad/s | gyro, bias removed, chip axes, mean since the last line |
| `ax ay az` | m/s² | accelerometer, chip axes, mean since the last line (chip facing down: az ≈ −9.81) |
| `pwmL pwmR` | −191..191 | duty the speed loop is applying |
| `flags` | bits | 1 = IMU data valid, 2 = drive enabled (`TICKS_PER_REV` set), 4 = stopped by the watchdog |

Travel totals, not speeds: a lost line loses nothing, the next difference covers it. A drop
in `ms` means the ESP32 restarted; the bridge takes the next line as its new reference.

**`#` log lines** at any time, e.g. `# IMU: ICM-20948 at 0x69, accel calibration loaded`,
`# gyro bias 0.412 -0.233 0.087 deg/s`, `# ready`, `# ERR unknown command 'q'`. The bridge
prints them in its log as `ESP32: ...`.

## Pi → ESP32
| Line | Meaning |
|------|---------|
| `S,<left>,<right>` | target speed of each side, m/s (clamped to ±0.5). Must repeat: stop after 0.5 s without one. The bridge sends it at 20 Hz |
| `G` | re-measure the gyro bias (robot still; refused while moving) |
| `w` `s` `a` `d` `x` | bench keys: forward, back, spin left, spin right at 0.15 m/s per side, stop. Stop after 3 s |

## Adding a line type (e.g. RSSI)
1. ESP32: send it with `pilink::send("R,...")` from the new module; a new first letter.
2. `esp32_bridge.py` `on_line()`: lines that don't start with `T,` are ignored today; add a
   branch for the new letter.
3. `fake_robot.py`: send the same line, so the tests cover it.
4. `selftest.py` `unit_checks()`: add a parse check; run `hw_selftest`.
The plan for RSSI: [[RSSI merge plan]].
