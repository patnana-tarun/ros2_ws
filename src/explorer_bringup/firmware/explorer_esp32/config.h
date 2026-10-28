// Explorer rover ESP32 controller: every pin, constant and gain in one place.
// Values come from rover_tests/ (sketches 1-4); the ones marked <-- must be set before driving.
#pragma once
#include <Arduino.h>

// ---------- Link to the Pi (USB serial) ----------
constexpr uint32_t BAUD           = 115200;
constexpr uint32_t TELEMETRY_MS   = 20;     // 50 Hz 'T' lines to the Pi
constexpr uint32_t CMD_TIMEOUT_MS = 500;    // 'S' commands: stop if the Pi goes silent
constexpr uint32_t KEY_TIMEOUT_MS = 3000;   // bench keys typed in the Serial Monitor
constexpr float    KEY_SPEED      = 0.15f;  // m/s per side for the bench keys

// ---------- Motors: 3x TB6612FNG, each side's channels wired together (test 1) ----------
constexpr int L_PWM = 25, L_IN1 = 26, L_IN2 = 27;
constexpr int R_PWM = 33, R_IN1 = 14, R_IN2 = 13;
constexpr int STBY  = 4;
constexpr bool INVERT_LEFT = false, INVERT_RIGHT = false;
constexpr int PWM_FREQ = 20000, PWM_RES = 8;
constexpr int MAX_DUTY = 191;               // ~75 %: motors rated 9 V, pack up to 12.6 V

// ---------- Encoders on the 4 corner wheels (test 3) ----------
constexpr bool ENC_QUADRATURE = true;       // false = A only; direction from the command
constexpr int ENC_A[4]    = {16, 18, 23, 35};   // LF, LR, RF, RR
constexpr int ENC_B[4]    = {17, 19, 34, 32};   // 34/35 have no pull-up: 10k to 3.3 V
constexpr int ENC_SIGN[4] = {1, 1, -1, -1};     // right side mirrored
constexpr float TICKS_PER_REV = 0;          // <-- from test 3 ('m'); 0 keeps the motors off
constexpr float WHEEL_DIAM_M  = 0.065f;

// ---------- Speed loop per side: feed-forward + PI on encoder speed (test 4) ----------
constexpr uint32_t CONTROL_MS = 20;         // 50 Hz
constexpr float KF = 400, KP = 300, KI = 800;   // <-- tuned values from test 4
constexpr float I_LIMIT   = 0.3f;           // anti-windup, m
constexpr float MAX_SPEED = 0.5f;           // m/s per side
constexpr float SPEED_LPF = 0.5f;           // smoothing of the measured speed (1 = none)

// ---------- IMU: SparkFun ICM-20948 over Qwiic/I2C (test 2, icm20948_i2c) ----------
constexpr int SDA_PIN = 21, SCL_PIN = 22;
constexpr uint32_t IMU_US = 5000;           // 200 Hz, averaged into each 'T' line
