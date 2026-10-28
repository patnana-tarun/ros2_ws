/*
  Explorer Rover - Test 6: Encoders + IMU (odometry, motors OFF)
  --------------------------------------------------------------
  Push the robot BY HAND on the floor. It computes position (x, y)
  and heading three ways so you can compare:
    encHead  = heading from encoders only (drifts when tracks slip)
    gyroHead = heading from gyro only
    fused    = 98% gyro + 2% encoders (complementary filter)
  x, y use encoder distance + fused heading.

  Before running: set TICKS_PER_REV (test 3) and GYRO_Z_BIAS (test 2).
  TRACK_WIDTH_M: distance between left and right wheel centres. Measure it.

  Serial Monitor 115200. Keys:  r = reset pose   p = print on/off
*/
#include <Wire.h>
#include "ICM_20948.h"

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
float TICKS_PER_REV  = 0;           // <-- from test 3
const float WHEEL_DIAM_M  = 0.065;
float TRACK_WIDTH_M  = 0.18;        // <-- measure left-to-right wheel centres

// ---------- IMU ----------
ICM_20948_I2C imu;
const int AD0_VAL = 1;
float GYRO_Z_BIAS = 0.0;            // <-- from test 2 (deg/s)
const float ALPHA = 0.98;           // trust in gyro

const int STBY = 4;

float x = 0, y = 0, thFused = 0, thEnc = 0, thGyro = 0;   // radians
long prev[4] = {0, 0, 0, 0};
float gyroAccum = 0;                // rad since last odom step
unsigned long lastUs = 0, lastOdomMs = 0;
bool printing = true;

float wrapPi(float a) { while (a > PI) a -= 2 * PI; while (a < -PI) a += 2 * PI; return a; }

void setup() {
  Serial.begin(115200);
  pinMode(STBY, OUTPUT); digitalWrite(STBY, LOW);   // motors off

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
  lastUs = micros(); lastOdomMs = millis();
  Serial.println("\nOdometry test. Push robot by hand. r=reset, p=print");
}

void loop() {
  // Gyro integrates as fast as data arrives
  if (imu.dataReady()) {
    imu.getAGMT();
    unsigned long now = micros();
    float dt = (now - lastUs) / 1e6; lastUs = now;
    float gz = imu.gyrZ() - GYRO_Z_BIAS;
    if (fabsf(gz) < 0.3) gz = 0;
    float dth = gz * DEG_TO_RAD * dt;
    gyroAccum += dth;
    thGyro = wrapPi(thGyro + dth);
  }

  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'r') { x = y = thFused = thEnc = thGyro = 0; Serial.println("Pose reset"); }
    if (c == 'p') printing = !printing;
  }

  // Odometry step at 50 Hz
  if (millis() - lastOdomMs >= 20) {
    lastOdomMs = millis();
    float d[4];
    for (int i = 0; i < 4; i++) { long c = readCount(i); d[i] = c - prev[i]; prev[i] = c; }
    float mpt = PI * WHEEL_DIAM_M / TICKS_PER_REV;
    float dL = (d[0] + d[1]) / 2 * mpt;
    float dR = (d[2] + d[3]) / 2 * mpt;
    float dist = (dL + dR) / 2;
    float dthEnc = (dR - dL) / TRACK_WIDTH_M;

    thEnc = wrapPi(thEnc + dthEnc);
    float dthFused = ALPHA * gyroAccum + (1 - ALPHA) * dthEnc;
    gyroAccum = 0;

    float mid = thFused + dthFused / 2;        // midpoint heading
    x += dist * cosf(mid);
    y += dist * sinf(mid);
    thFused = wrapPi(thFused + dthFused);
  }

  static unsigned long lp = 0;
  if (printing && millis() - lp > 200) {
    lp = millis();
    Serial.printf("x=%6.3f y=%6.3f m | fused=%7.2f gyro=%7.2f enc=%7.2f deg\n",
                  x, y, thFused * RAD_TO_DEG, thGyro * RAD_TO_DEG, thEnc * RAD_TO_DEG);
  }
}
