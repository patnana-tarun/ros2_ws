---
tags: [robot]
---
# Wiring

From the user's test sketches (rover_tests, 2026-10-28). The authoritative copy is
`src/explorer_bringup/firmware/explorer_esp32/config.h`; change a pin there, then reflash.
Board: ESP32 DevKit V1 (ESP-WROOM-32). Arduino board name: *ESP32 Dev Module*.

## Motors: 3 × TB6612FNG, six BO motors
Each side's three motor channels share one set of control lines, so a side is driven as one.

| Driver | Output A | Output B |
|--------|----------|----------|
| 1 | left middle | left front |
| 2 | left rear | right rear |
| 3 | right front | right middle |

| ESP32 GPIO | Goes to | Signal |
|-----------|---------|--------|
| 25 | D1 PWMA, D1 PWMB, D2 PWMA | left speed (PWM) |
| 26 | D1 AIN1, D1 BIN1, D2 AIN1 | left direction 1 |
| 27 | D1 AIN2, D1 BIN2, D2 AIN2 | left direction 2 |
| 33 | D2 PWMB, D3 PWMA, D3 PWMB | right speed (PWM) |
| 14 | D2 BIN1, D3 AIN1, D3 BIN1 | right direction 1 |
| 13 | D2 BIN2, D3 AIN2, D3 BIN2 | right direction 2 |
| 4 | STBY on all three drivers, plus 10 kΩ to GND | enable (low = motors off) |

- A whole side turning the wrong way: set `INVERT_LEFT` / `INVERT_RIGHT` in `config.h`. One
  motor turning against its side: swap that motor's two wires.
- Duty is capped at 191/255 (~75 %): the motors are rated 9 V and the pack gives up to 12.6 V.
- Drivers: VM = battery, VCC = logic supply (the TB6612FNG accepts 2.7–5.5 V; 3.3 V from the
  ESP32 matches its signal levels), all grounds common. The power wiring was not given in the
  test sketches; this is the usual way, check it against the robot.

## Encoders: the four corner wheels
| Wheel | A | B |
|-------|---|---|
| left front | 16 | 17 |
| left rear | 18 | 19 |
| right front | 23 | 34 |
| right rear | 35 | 32 |

- **GPIO 34 and 35 are input-only and have no internal pull-up.** Add 10 kΩ from each to
  3.3 V unless the encoder board has its own pull-ups.
- Counted on the rising edge of A; B gives the direction (`ENC_QUADRATURE = true`). Encoders
  with one output: `ENC_QUADRATURE = false`, and the direction is taken from the command.
- The right side is mirrored (`ENC_SIGN = {1, 1, -1, -1}`). A wheel that counts backwards
  when driven forward: flip its sign in `ENC_SIGN`.
- The middle wheels have no encoders; their angle on `/joint_states` is the mean of the side.

## IMU: SparkFun ICM-20948 (Qwiic)
| Qwiic wire | ESP32 |
|------------|-------|
| black GND | GND |
| red 3V3 | 3V3 (**never 5 V**) |
| blue SDA | 21 |
| yellow SCL | 22 |

The breakout has its own 2.2 kΩ pull-ups. Address 0x69 (default) or 0x68 (AD0 jumper
closed); the firmware tries both. Mounting: the robot model expects the chip at the centre,
facing down ([[Robot model]]); check it in step 4 of [[Hardware bring-up]].

## USB and power
- ESP32 → Pi: USB cable (power and serial). YDLIDAR X2 → Pi: its USB adapter (power, serial,
  and DTR switches the motor). Both show up as `/dev/ttyUSB*`, in either order; use
  `/dev/serial/by-path/...` names, which follow the USB socket.
- Power the ESP32 from the Pi's USB (logic), never from the motor supply. Keep one common
  ground. A capacitor across each driver's VM helps against motor noise resetting the ESP32.
- Pins not to use: 0, 2, 5, 12, 15 (boot straps), 6–11 (flash), 1 and 3 (USB serial).
