---
tags: [robot]
source: src/explorer_bringup/firmware/explorer_esp32/
---
# ESP32 firmware

`src/explorer_bringup/firmware/explorer_esp32/`: one Arduino sketch, one header per job, no
external libraries. Needs the **ESP32 Arduino core 3.x** (it uses `ledcAttach`; core 2.x
fails with "ledcAttach was not declared"). Built and checked with core 3.3.12: about 330 KB
of flash (25 %), 24 KB of RAM. What it talks: [[Serial protocol]]. Pins: [[Wiring]].

## Files
| File | Job |
|------|-----|
| `config.h` | every pin, constant and gain; the only file to edit for calibration |
| `motors.h` | TB6612FNG: `set(left, right)` duty −191..191; 0 brakes; both 0 → standby |
| `encoders.h` | 4 encoder interrupts; `step()` returns each wheel's travel (m) since the last call and adds it to `total[]` |
| `imu.h` | ICM-20948 by registers: init, gyro bias at boot, flash calibration, 200 Hz sampling, averaging |
| `pilink.h` | the serial line protocol: checksum, `send()`, `receive()` |
| `explorer_esp32.ino` | `setup()`, `loop()`, command handling, the speed loop, telemetry |

## What `loop()` does
1. `imu::poll()`: every 5 ms reads accel + gyro and adds them to running sums.
2. `pilink::receive()`: a complete, checksum-valid line → `handle()`: `S` sets the targets,
   `G` re-measures the gyro bias, `w s a d x` are bench keys.
3. Every 20 ms, `control()`:
   - **watchdog**: no `S` for 0.5 s (no key for 3 s) → targets 0, flag 4 set;
   - **encoders**: travel per wheel; a side's speed = mean of its front and rear wheel, then
     smoothed (`SPEED_LPF` 0.5);
   - **speed loop** per side: duty = `KF`·target + `KP`·error + `KI`·∫error, the integral
     clamped to ±`I_LIMIT`; a zero target gives duty 0 (brake) and clears the integral;
   - motors set. While `TICKS_PER_REV` is 0 the duty is always 0 (drive disabled, flag 2 off).
4. Every 20 ms, `telemetry()`: one `T` line with the total travel of each wheel, the IMU
   averages since the last line, both duties and the flags.

## IMU details
- Gyro ±250 °/s, accel ±2 g, both with the chip's low-pass filter at ~50 Hz (cuts motor
  vibration). Sampled at 200 Hz; each `T` line carries the mean of the ~4 samples since the
  last one, so no rotation between lines is lost.
- **Gyro bias** is measured at every boot: 800 samples (~1.6 s). If the gyro's spread is above
  1 °/s the robot was moving, and it retries (up to 3 times). **Keep the robot still for
  2 s after power-on or reset.** `G` repeats it later (only while stopped).
- **Accel calibration** (optional; the EKF does not use the accelerometer today): the 6-face
  calibration of `firmware/icm20948_calibration` is saved in flash (namespace `icm20948`) and
  loaded at boot. The boot message says whether it was found.
- Data are sent in the chip's own axes. The URDF's `imu_joint` rotates them into the robot frame.
- The magnetometer is not used (motors and rock make it unreliable).

## Settings in `config.h` to set before driving
| Setting | Now | Set from |
|---------|-----|----------|
| `TICKS_PER_REV` | **0 = drive disabled** | rover_tests 3, key `m` (ticks for 10 wheel turns / 10) |
| `KF`, `KP`, `KI` | 400, 300, 800 (rover_tests' start values) | rover_tests 4: raise KP until the speed follows, KI until the steady error goes, back off if it oscillates |
| `INVERT_LEFT/RIGHT`, `ENC_SIGN` | false, {1,1,−1,−1} | rover_tests 1 and 3 |
| `ENC_QUADRATURE` | true | false if the encoders have only one output |
| `WHEEL_DIAM_M` | 0.065 | measure the wheel |
| `KEY_SPEED` | 0.15 m/s | bench keys only |

## Build and flash
- Arduino IDE 2: open `explorer_esp32.ino`, board *ESP32 Dev Module*, port, Upload.
- Command line: `arduino-cli compile --upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 src/explorer_bringup/firmware/explorer_esp32`
- Stop `robot.launch.py` first (it holds the port). If the upload hangs at "Connecting...",
  hold the board's BOOT button until it starts.
- The colcon build also copies the sketches to `install/explorer_bringup/share/explorer_bringup/firmware/`.

## Changing it
- New sensor: a new header with `begin()` and `poll()`, called from `setup()`/`loop()`; its
  data go out on a new line type ([[Serial protocol]], "Adding a line type").
- Keep `loop()` free of `delay()`: the speed loop and the watchdog depend on it running often.
  (The only blocking parts are at boot and the `G` command, while the motors are off.)
