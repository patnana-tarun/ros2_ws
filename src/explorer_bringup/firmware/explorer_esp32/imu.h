// ICM-20948 accel + gyro over I2C, register-level (from icm20948_i2c.ino, no library).
// Gyro bias is measured at boot (robot still). Accel offset/scale come from the 6-face
// calibration that icm20948_i2c.ino saved in flash (namespace "icm20948"), if it was run.
// Samples are averaged between telemetry lines; output is in the chip's own axes
// (rad/s, m/s^2) - the URDF imu_link joint rotates them into the robot frame.
#pragma once
#include <Preferences.h>
#include <Wire.h>
#include "config.h"

namespace imu {

constexpr uint8_t WHO_AM_I = 0x00, USER_CTRL = 0x03, PWR_MGMT_1 = 0x06, PWR_MGMT_2 = 0x07,
                  ACCEL_XOUT_H = 0x2D, BANK_SEL = 0x7F;                     // bank 0
constexpr uint8_t GYRO_SMPLRT_DIV = 0x00, GYRO_CONFIG_1 = 0x01,
                  ACCEL_SMPLRT_DIV_2 = 0x11, ACCEL_CONFIG = 0x14;           // bank 2
constexpr float G = 9.80665f;

// Same layout as icm20948_i2c.ino so its saved calibration loads unchanged
struct Calibration {
  uint32_t magic;
  float accOff[3], accScale[3];
  float magOff[3], magScale[3];
  bool accDone, magDone;
};
constexpr uint32_t CAL_MAGIC = 0x1C20948A;

uint8_t addr = 0;
bool ok = false;
Calibration cal = {CAL_MAGIC, {0, 0, 0}, {1, 1, 1}, {0, 0, 0}, {1, 1, 1}, false, false};
float bias[3] = {0, 0, 0};                  // deg/s
float sumG[3], sumA[3];
uint32_t n = 0, lastUs = 0;

inline bool write(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

inline bool read(uint8_t reg, uint8_t *buf, uint8_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0 || Wire.requestFrom(addr, len) != len) return false;
  for (uint8_t i = 0; i < len; i++) buf[i] = Wire.read();
  return true;
}

// accel in g (calibrated), gyro in deg/s (bias not removed)
inline bool sample(float a[3], float g[3]) {
  uint8_t b[12];
  if (!read(ACCEL_XOUT_H, b, 12)) return false;
  for (int k = 0; k < 3; k++) {
    a[k] = ((int16_t)(b[2 * k] << 8 | b[2 * k + 1]) / 16384.0f - cal.accOff[k]) / cal.accScale[k];
    g[k] = (int16_t)(b[6 + 2 * k] << 8 | b[7 + 2 * k]) / 131.0f;
  }
  return true;
}

// Mean gyro over ~2 s; retries (up to 3 times) while the robot is being moved
inline void calibrateGyro() {
  for (int attempt = 0; attempt < 3; attempt++) {
    double s[3] = {0, 0, 0}, s2[3] = {0, 0, 0};
    float a[3], g[3];
    int m = 0;
    for (int i = 0; i < 800; i++) {
      delay(2);
      if (!sample(a, g)) continue;
      for (int k = 0; k < 3; k++) { s[k] += g[k]; s2[k] += g[k] * g[k]; }
      m++;
    }
    if (m < 400) break;
    bool still = true;
    for (int k = 0; k < 3; k++) {
      bias[k] = s[k] / m;
      still &= s2[k] / m - bias[k] * bias[k] < 1.0;   // gyro sd < 1 deg/s
    }
    Serial.printf("# gyro bias %.3f %.3f %.3f deg/s%s\n", bias[0], bias[1], bias[2],
                  still ? "" : " (robot moved - retrying)");
    if (still) break;
  }
  n = 0;
}

inline bool begin() {
  Wire.begin(SDA_PIN, SCL_PIN, 400000);
  Wire.setTimeOut(5);
  for (uint8_t a : {0x69, 0x68}) {          // SparkFun default 0x69, AD0 jumper closed 0x68
    addr = a;
    uint8_t id = 0;
    if (read(WHO_AM_I, &id, 1) && id == 0xEA) break;
    addr = 0;
  }
  if (!addr) { Serial.println("# IMU: no ICM-20948 at 0x69/0x68"); return ok = false; }
  write(BANK_SEL, 0);
  write(PWR_MGMT_1, 0x80);                  // reset
  delay(100);
  write(PWR_MGMT_1, 0x01);                  // wake, auto clock
  delay(50);
  write(PWR_MGMT_2, 0x00);                  // accel + gyro on
  write(BANK_SEL, 2 << 4);
  write(GYRO_SMPLRT_DIV, 0x00);
  write(GYRO_CONFIG_1, 0x19);               // +/-250 deg/s, DLPF ~51 Hz
  write(ACCEL_SMPLRT_DIV_2, 0x00);
  write(ACCEL_CONFIG, 0x19);                // +/-2 g, DLPF ~50 Hz
  write(BANK_SEL, 0);
  write(USER_CTRL, 0x00);

  Preferences prefs;
  Calibration c;
  prefs.begin("icm20948", true);
  if (prefs.getBytes("cal", &c, sizeof(c)) == sizeof(c) && c.magic == CAL_MAGIC && c.accDone) cal = c;
  prefs.end();
  Serial.printf("# IMU: ICM-20948 at 0x%02X, accel calibration %s\n", addr,
                cal.accDone ? "loaded" : "not done (optional: icm20948_i2c.ino 'a')");
  calibrateGyro();
  lastUs = micros();
  return ok = true;
}

// Call often; samples at IMU_US and accumulates for the next average
inline void poll() {
  if (!addr || micros() - lastUs < IMU_US) return;
  lastUs = micros();
  float a[3], g[3];
  ok = sample(a, g);
  if (!ok) return;
  for (int k = 0; k < 3; k++) { sumA[k] += a[k]; sumG[k] += g[k]; }
  n++;
}

// Mean since the last call: gyro rad/s (bias removed), accel m/s^2. False if no sample.
inline bool take(float gyro[3], float acc[3]) {
  if (!n) return false;
  for (int k = 0; k < 3; k++) {
    gyro[k] = (sumG[k] / n - bias[k]) * DEG_TO_RAD;
    acc[k] = sumA[k] / n * G;
    sumG[k] = sumA[k] = 0;
  }
  n = 0;
  return true;
}

}  // namespace imu
