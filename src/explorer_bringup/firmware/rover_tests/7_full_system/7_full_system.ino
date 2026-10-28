/*
  Explorer Rover - Test 7: Motors + Encoders + IMU (full system)
  --------------------------------------------------------------
  This is the shape of the final ESP32 firmware:
    cmd (v, w)  ->  wheel targets  ->  PI speed loop (encoders)  ->  motors
    encoders + gyro  ->  fused odometry (x, y, theta)  ->  printed for the Pi
    watchdog stops motors if commands stop

  Set first: TICKS_PER_REV (test 3), GYRO_Z_BIAS (test 2), TRACK_WIDTH_M,
  and Kp/Ki you found in test 4.

  Serial Monitor 115200 ("Newline" line ending). Two ways to command:
    Keys:  w s a d = forward / reverse / spin left / spin right,  x = stop
    Line:  v 0.20 0.0     -> linear 0.20 m/s, angular 0.0 rad/s
           v 0.0 1.0      -> spin left at 1 rad/s
           r              -> reset odometry
  The Pi will later send the same "v <lin> <ang>" line at ~10-20 Hz.

  Watchdog: "v" commands stop after 0.5 s of silence; keys after 3 s.
  Output (10 Hz):
    ODOM x y theta_deg v_meas w_meas | pwmL pwmR
*/
#include <Wire.h>
#include "ICM_20948.h"

// ---------- Motors ----------
const int L_PWM = 25, L_IN1 = 26, L_IN2 = 27;
const int R_PWM = 33, R_IN1 = 14, R_IN2 = 13;
const int STBY  = 4;
const bool INVERT_LEFT = false, INVERT_RIGHT = false;
const int PWM_FREQ = 20000, PWM_RES = 8, MAX_DUTY = 191;

// ---------- Encoders ----------
const bool ENC_QUADRATURE = true;
const int ENC_A[4] = {16, 18, 23, 35};   // LF, LR, RF, RR
const int ENC_B[4] = {17, 19, 34, 32};
const int ENC_SIGN[4] = {1, 1, -1, -1};
volatile long encCount[4] = {0, 0, 0, 0};
void IRAM_ATTR isr0() { encCount[0] += (!ENC_QUADRATURE || digitalRead(ENC_B[0])) ? 1 : -1; }
void IRAM_ATTR isr1() { encCount[1] += (!ENC_QUADRATURE || digitalRead(ENC_B[1])) ? 1 : -1; }
void IRAM_ATTR isr2() { encCount[2] += (!ENC_QUADRATURE || digitalRead(ENC_B[2])) ? 1 : -1; }
void IRAM_ATTR isr3() { encCount[3] += (!ENC_QUADRATURE || digitalRead(ENC_B[3])) ? 1 : -1; }
void (*isrs[4])() = {isr0, isr1, isr2, isr3};
long readCount(int i) { noInterrupts(); long c = encCount[i]; interrupts(); return c * ENC_SIGN[i]; }

// ---------- Geometry ----------
float TICKS_PER_REV = 0;            // <-- from test 3
const float WHEEL_DIAM_M = 0.065;
float TRACK_WIDTH_M = 0.18;         // <-- measure

// ---------- IMU ----------
ICM_20948_I2C imu;
const int AD0_VAL = 1;
float GYRO_Z_BIAS = 0.0;            // <-- from test 2
const float ALPHA = 0.98;

// ---------- Control ----------
float Kp = 300, Ki = 800, KF = 400; // <-- from test 4
const float MAX_SPEED = 0.5;        // m/s per side
float tgtL = 0, tgtR = 0, intL = 0, intR = 0;
int pwmL = 0, pwmR = 0;
unsigned long lastCmdMs = 0, timeoutMs = 3000;

// ---------- Odometry ----------
float x = 0, y = 0, th = 0, vMeas = 0, wMeas = 0;
long prev[4] = {0, 0, 0, 0};
float gyroAccum = 0;
unsigned long lastUs = 0, lastLoopMs = 0;
String line;

float wrapPi(float a) { while (a > PI) a -= 2 * PI; while (a < -PI) a += 2 * PI; return a; }

void driveSide(int pwmPin, int in1, int in2, int speed, bool inv) {
  if (inv) speed = -speed;
  speed = constrain(speed, -MAX_DUTY, MAX_DUTY);
  if (speed > 0)      { digitalWrite(in1, HIGH); digitalWrite(in2, LOW);  }
  else if (speed < 0) { digitalWrite(in1, LOW);  digitalWrite(in2, HIGH); }
  else                { digitalWrite(in1, HIGH); digitalWrite(in2, HIGH); }
  ledcWrite(pwmPin, abs(speed));
}

void setCmd(float v, float w, unsigned long timeout) {
  float l = v - w * TRACK_WIDTH_M / 2;
  float r = v + w * TRACK_WIDTH_M / 2;
  tgtL = constrain(l, -MAX_SPEED, MAX_SPEED);
  tgtR = constrain(r, -MAX_SPEED, MAX_SPEED);
  if (tgtL == 0) intL = 0;
  if (tgtR == 0) intR = 0;
  timeoutMs = timeout;
  lastCmdMs = millis();
}

int pi(float tgt, float meas, float &integ, float dt) {
  if (tgt == 0) { integ = 0; return 0; }
  float err = tgt - meas;
  integ = constrain(integ + err * dt, -0.3, 0.3);
  return (int)(KF * tgt + Kp * err + Ki * integ);
}

void handleLine(String s) {
  s.trim();
  if (s.length() == 0) return;
  if (s.length() == 1) {
    float v = 0.2, w = 1.5;
    switch (s[0]) {
      case 'w': setCmd( v, 0, 3000); return;
      case 's': setCmd(-v, 0, 3000); return;
      case 'a': setCmd(0,  w, 3000); return;
      case 'd': setCmd(0, -w, 3000); return;
      case 'x': setCmd(0,  0, 3000); return;
      case 'r': x = y = th = 0; Serial.println("Odom reset"); return;
    }
  }
  if (s[0] == 'v') {
    float v = 0, w = 0;
    if (sscanf(s.c_str(), "v %f %f", &v, &w) == 2) { setCmd(v, w, 500); return; }
  }
  Serial.println("ERR unknown command");
}

void setup() {
  Serial.begin(115200);
  pinMode(STBY, OUTPUT); digitalWrite(STBY, LOW);
  pinMode(L_IN1, OUTPUT); pinMode(L_IN2, OUTPUT);
  pinMode(R_IN1, OUTPUT); pinMode(R_IN2, OUTPUT);
  ledcAttach(L_PWM, PWM_FREQ, PWM_RES);
  ledcAttach(R_PWM, PWM_FREQ, PWM_RES);

  for (int i = 0; i < 4; i++) {
    pinMode(ENC_A[i], INPUT_PULLUP);
    if (ENC_QUADRATURE) pinMode(ENC_B[i], INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(ENC_A[i]), isrs[i], RISING);
  }

  Wire.begin(21, 22); Wire.setClock(400000);
  while (true) {
    imu.begin(Wire, AD0_VAL);
    if (imu.status == ICM_20948_Stat_Ok) break;
    Serial.println("IMU not found, retrying..."); delay(1000);
  }
  ICM_20948_fss_t fss; fss.a = gpm2; fss.g = dps500;
  imu.setFullScale((ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr), fss);
  ICM_20948_dlpcfg_t dlp; dlp.a = acc_d23bw9_n34bw4; dlp.g = gyr_d23bw9_n35bw9;
  imu.setDLPFcfg((ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr), dlp);
  imu.enableDLPF(ICM_20948_Internal_Gyr, true);

  if (TICKS_PER_REV <= 0) { Serial.println("Set TICKS_PER_REV first!"); while (true) delay(1000); }
  lastUs = micros(); lastLoopMs = millis();
  Serial.println("\nFull system ready. Keys w/s/a/d/x/r or 'v <lin> <ang>'");
}

void loop() {
  // 1. Gyro
  if (imu.dataReady()) {
    imu.getAGMT();
    unsigned long now = micros();
    float dt = (now - lastUs) / 1e6; lastUs = now;
    float gz = imu.gyrZ() - GYRO_Z_BIAS;
    if (fabsf(gz) < 0.3) gz = 0;
    gyroAccum += gz * DEG_TO_RAD * dt;
  }

  // 2. Commands
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { handleLine(line); line = ""; }
    else if (line.length() < 40) line += c;
  }

  // 3. Watchdog
  if ((tgtL != 0 || tgtR != 0) && millis() - lastCmdMs > timeoutMs) {
    setCmd(0, 0, 3000);
    Serial.println("WATCHDOG stop");
  }

  // 4. Control + odometry at 50 Hz
  unsigned long now = millis();
  if (now - lastLoopMs >= 20) {
    float dt = (now - lastLoopMs) / 1000.0;
    lastLoopMs = now;

    float d[4];
    for (int i = 0; i < 4; i++) { long c = readCount(i); d[i] = c - prev[i]; prev[i] = c; }
    if (!ENC_QUADRATURE) {
      float sL = (tgtL >= 0) ? 1 : -1, sR = (tgtR >= 0) ? 1 : -1;
      d[0] = fabsf(d[0]) * sL; d[1] = fabsf(d[1]) * sL;
      d[2] = fabsf(d[2]) * sR; d[3] = fabsf(d[3]) * sR;
    }
    float mpt = PI * WHEEL_DIAM_M / TICKS_PER_REV;
    float dL = (d[0] + d[1]) / 2 * mpt;
    float dR = (d[2] + d[3]) / 2 * mpt;

    // speed loop
    pwmL = pi(tgtL, dL / dt, intL, dt);
    pwmR = pi(tgtR, dR / dt, intR, dt);
    digitalWrite(STBY, (pwmL || pwmR) ? HIGH : LOW);
    driveSide(L_PWM, L_IN1, L_IN2, pwmL, INVERT_LEFT);
    driveSide(R_PWM, R_IN1, R_IN2, pwmR, INVERT_RIGHT);

    // fused odometry
    float dist = (dL + dR) / 2;
    float dthEnc = (dR - dL) / TRACK_WIDTH_M;
    float dth = ALPHA * gyroAccum + (1 - ALPHA) * dthEnc;
    gyroAccum = 0;
    float mid = th + dth / 2;
    x += dist * cosf(mid);
    y += dist * sinf(mid);
    th = wrapPi(th + dth);
    vMeas = dist / dt;
    wMeas = dth / dt;
  }

  // 5. Report at 10 Hz
  static unsigned long lp = 0;
  if (millis() - lp >= 100) {
    lp = millis();
    Serial.printf("ODOM %.3f %.3f %.2f %.3f %.3f | %d %d\n",
                  x, y, th * RAD_TO_DEG, vMeas, wMeas, pwmL, pwmR);
  }
}
