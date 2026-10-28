/*
  Explorer rover - ESP32 low-level controller (the Pi is the brain, this is the controller)
  ----------------------------------------------------------------------------------------
  Pi --S,<left>,<right>--> per-side PI speed loop on the encoders --> TB6612FNG motors
  Pi <--T lines, 50 Hz---- wheel travel (4 encoders) + averaged ICM-20948 gyro/accel
  The Pi (explorer_bringup esp32_bridge) turns T lines into /wheel/odom, /joint_states and
  /imu; the robot_localization EKF fuses them. Protocol: pilink.h. Settings: config.h.

  Board: ESP32 Dev Module, ESP32 Arduino core 3.x. No libraries needed.
  Before driving: set TICKS_PER_REV (rover_tests 3) in config.h. Until then the motors stay
  off and only the IMU is reported. Keep the robot still for 2 s after reset (gyro bias).

  Bench test in the Serial Monitor (115200, Newline): w s a d = forward / back / spin
  left / spin right at KEY_SPEED, x = stop, G = re-measure the gyro bias.
*/
#include "config.h"
#include "encoders.h"
#include "imu.h"
#include "pilink.h"
#include "motors.h"

float tgt[2] = {0, 0};                      // left, right target speed, m/s
float meas[2] = {0, 0};                     // measured (smoothed) speed, m/s
float integ[2] = {0, 0};
int pwm[2] = {0, 0};
int dir[2] = {1, 1};                        // last commanded direction (single-channel encoders)
uint32_t lastCmdMs = 0, timeoutMs = CMD_TIMEOUT_MS, lastControlMs = 0;
bool watchdogStop = false;
constexpr bool DRIVE_OK = TICKS_PER_REV > 0;

void setTargets(float l, float r, uint32_t timeout) {
  tgt[0] = constrain(l, -MAX_SPEED, MAX_SPEED);
  tgt[1] = constrain(r, -MAX_SPEED, MAX_SPEED);
  timeoutMs = timeout;
  lastCmdMs = millis();
  watchdogStop = false;
}

void handle(const char *cmd) {
  float l, r;
  if (sscanf(cmd, "S,%f,%f", &l, &r) == 2) { setTargets(l, r, CMD_TIMEOUT_MS); return; }
  const float v = KEY_SPEED;
  switch (cmd[1] ? 0 : cmd[0]) {            // single-character commands only
    case 'w': setTargets( v,  v, KEY_TIMEOUT_MS); return;
    case 's': setTargets(-v, -v, KEY_TIMEOUT_MS); return;
    case 'a': setTargets(-v,  v, KEY_TIMEOUT_MS); return;
    case 'd': setTargets( v, -v, KEY_TIMEOUT_MS); return;
    case 'x': setTargets( 0,  0, KEY_TIMEOUT_MS); return;
    case 'G':
      if (pwm[0] || pwm[1]) Serial.println("# ERR stop the robot before G");
      else imu::calibrateGyro();
      return;
  }
  Serial.printf("# ERR unknown command '%s'\n", cmd);
}

// Feed-forward + PI with anti-windup; a zero target brakes and clears the integral
int speedLoop(int s, float dt) {
  if (tgt[s] == 0) { integ[s] = 0; return 0; }
  float err = tgt[s] - meas[s];
  integ[s] = constrain(integ[s] + err * dt, -I_LIMIT, I_LIMIT);
  return (int)(KF * tgt[s] + KP * err + KI * integ[s]);
}

void control() {
  uint32_t now = millis();
  float dt = (now - lastControlMs) / 1000.0f;
  lastControlMs = now;

  if ((tgt[0] || tgt[1]) && now - lastCmdMs > timeoutMs) {
    tgt[0] = tgt[1] = 0;
    watchdogStop = true;
  }
  for (int s = 0; s < 2; s++) if (tgt[s]) dir[s] = tgt[s] > 0 ? 1 : -1;

  float d[4];
  encoders::step(d, dir[0], dir[1]);
  for (int s = 0; s < 2; s++) {
    float v = (d[2 * s] + d[2 * s + 1]) / 2 / dt;   // front + rear of the side
    meas[s] += SPEED_LPF * (v - meas[s]);
    pwm[s] = DRIVE_OK ? speedLoop(s, dt) : 0;
  }
  motors::set(pwm[0], pwm[1]);
}

void telemetry() {
  float g[3] = {0, 0, 0}, a[3] = {0, 0, 0};
  uint8_t flags = (imu::take(g, a) ? pilink::IMU_OK : 0) | (DRIVE_OK ? pilink::DRIVE_OK : 0) |
                  (watchdogStop ? pilink::WATCHDOG : 0);
  long um[4];
  for (int i = 0; i < 4; i++) um[i] = lround(encoders::total[i] * 1e6);
  pilink::send("T,%lu,%ld,%ld,%ld,%ld,%.5f,%.5f,%.5f,%.3f,%.3f,%.3f,%d,%d,%u",
             (unsigned long)millis(), um[0], um[1], um[2], um[3],
             g[0], g[1], g[2], a[0], a[1], a[2], pwm[0], pwm[1], flags);
}

void setup() {
  Serial.setTxBufferSize(1024);             // a T line never waits for the UART
  Serial.begin(BAUD);
  motors::begin();
  encoders::begin();
  delay(200);
  Serial.println("\n# explorer_esp32 starting - keep the robot still");
  imu::begin();
  if (!DRIVE_OK) Serial.println("# TICKS_PER_REV not set in config.h: motors disabled");
  Serial.println("# ready");
  lastControlMs = millis();
}

void loop() {
  imu::poll();
  if (const char *cmd = pilink::receive()) handle(cmd);

  static uint32_t lastTelemetryMs = 0;
  if (millis() - lastControlMs >= CONTROL_MS) control();
  if (millis() - lastTelemetryMs >= TELEMETRY_MS) {
    lastTelemetryMs = millis();
    telemetry();
  }
}
