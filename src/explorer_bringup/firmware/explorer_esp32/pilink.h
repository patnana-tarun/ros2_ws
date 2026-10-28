// Line protocol with the Pi over USB serial. Every line may end in "*HH", the XOR of
// the characters before the '*' (as in NMEA); lines that carry one are checked.
//
//   ESP32 -> Pi  T,<ms>,<lf>,<lr>,<rf>,<rr>,<gx>,<gy>,<gz>,<ax>,<ay>,<az>,<pwmL>,<pwmR>,<flags>*HH
//                  wheel travel since boot in micrometres (left front, left rear, right front,
//                  right rear), gyro rad/s and accel m/s^2 in IMU chip axes, PWM duty per side
//                  flags: 1 = IMU data valid, 2 = drive enabled, 4 = stopped by the watchdog
//                # <text>       log message
//   Pi -> ESP32  S,<left>,<right>   wheel speed targets per side, m/s (watchdog CMD_TIMEOUT_MS)
//                G                  re-measure the gyro bias (robot still; only while stopped)
//                w s a d x          bench keys from the Serial Monitor (KEY_TIMEOUT_MS)
#pragma once
#include "config.h"

namespace pilink {

enum Flags : uint8_t { IMU_OK = 1, DRIVE_OK = 2, WATCHDOG = 4 };

inline uint8_t checksum(const char *s, size_t len) {
  uint8_t c = 0;
  for (size_t i = 0; i < len; i++) c ^= s[i];
  return c;
}

// Sends one line with its checksum
inline void send(const char *fmt, ...) {
  char buf[200];
  va_list args;
  va_start(args, fmt);
  int len = vsnprintf(buf, sizeof(buf) - 5, fmt, args);
  va_end(args);
  if (len < 0) return;
  len = min(len, (int)sizeof(buf) - 6);
  snprintf(buf + len, 6, "*%02X\n", checksum(buf, len));
  Serial.write(buf, len + 4);
}

// Returns a complete, checksum-valid line (without "*HH"), or nullptr
inline const char *receive() {
  static char line[64];
  static size_t len = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c != '\n' && c != '\r') {
      if (len < sizeof(line) - 1) line[len++] = c;
      continue;
    }
    if (!len) continue;
    line[len] = 0;
    len = 0;
    char *star = strchr(line, '*');
    if (star) {
      *star = 0;
      if (strtoul(star + 1, nullptr, 16) != checksum(line, star - line)) {
        Serial.println("# ERR checksum");
        continue;
      }
    }
    return line;
  }
  return nullptr;
}

}  // namespace pilink
