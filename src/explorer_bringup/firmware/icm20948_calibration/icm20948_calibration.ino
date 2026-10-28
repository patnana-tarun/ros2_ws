/*
  SparkFun Qwiic 9DoF ICM-20948 on ESP32 DevKit - I2C mode

  Wiring (Qwiic cable colour / breakout pin -> ESP32 pin):
    Black  GND -> GND
    Red    3V3 -> 3V3      (3.3 V only - never 5 V/VIN)
    Blue   SDA -> GPIO 21  (D21)
    Yellow SCL -> GPIO 22  (D22)
  The board has its own 2.2k pull-ups, so no external resistors are needed.
  I2C address: 0x69 by default, 0x68 if the AD0 jumper is closed.

  The AK09916 magnetometer sits behind the ICM-20948. In I2C mode we turn on
  "bypass" so it appears directly on the ESP32's I2C bus at 0x0C.

  Serial commands (115200 baud):
    a = calibrate accelerometer (6 positions: lay each face of the board down)
    m = calibrate magnetometer (rotate slowly in all directions for 20 s)
    c = recalibrate gyro (keep still) - also done automatically at every boot
    p = print per-axis calibration + live axis report
    z = zero yaw
    r = erase saved calibration
  Accel and mag calibration are saved in flash and loaded at boot.
*/

#include <Wire.h>
#include <Preferences.h>

static const int PIN_SDA = 21;
static const int PIN_SCL = 22;

// ICM-20948 registers (bank 0 unless noted)
#define REG_WHO_AM_I        0x00   // expect 0xEA
#define REG_USER_CTRL       0x03
#define REG_PWR_MGMT_1      0x06
#define REG_PWR_MGMT_2      0x07
#define REG_INT_PIN_CFG     0x0F
#define REG_ACCEL_XOUT_H    0x2D   // accel(6) gyro(6) temp(2)
#define REG_BANK_SEL        0x7F
#define B2_GYRO_SMPLRT_DIV  0x00
#define B2_GYRO_CONFIG_1    0x01
#define B2_ACCEL_SMPLRT_DIV_2 0x11
#define B2_ACCEL_CONFIG     0x14

// AK09916 magnetometer registers
#define AK_ADDR   0x0C
#define AK_WIA2   0x01   // expect 0x09
#define AK_ST1    0x10
#define AK_HXL    0x11
#define AK_CNTL2  0x31
#define AK_CNTL3  0x32

uint8_t imuAddr = 0;
bool magOk = false;

float gyroBias[3] = {0, 0, 0};

// Saved calibration (accel: corrected = (raw - off) / scale, mag: (raw - off) * scale)
struct Calibration {
  uint32_t magic;
  float accOff[3], accScale[3];
  float magOff[3], magScale[3];
  bool accDone, magDone;
};
const uint32_t CAL_MAGIC = 0x1C20948A;
Calibration cal;
Preferences prefs;
float roll = 0, pitch = 0, yaw = 0;   // degrees
float lastMag[3] = {0, 0, 0};
uint32_t lastUpdateUs = 0, lastPrintMs = 0;

const float ALPHA = 0.98f;            // complementary filter weight on gyro
const uint32_t UPDATE_US = 5000;      // 200 Hz filter rate
const uint32_t PRINT_MS = 200;        // 5 Hz print rate

struct Sample {
  float ax, ay, az;   // g
  float gx, gy, gz;   // deg/s (raw, before bias removal)
  float temp;         // C
};

bool writeReg(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

bool readRegs(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, len) != len) return false;
  for (uint8_t i = 0; i < len; i++) buf[i] = Wire.read();
  return true;
}

uint8_t readReg(uint8_t addr, uint8_t reg) {
  uint8_t v = 0xEE;
  readRegs(addr, reg, &v, 1);
  return v;
}

void selectBank(uint8_t bank) {
  writeReg(imuAddr, REG_BANK_SEL, bank << 4);
}

// GPIO21/22 have no ADC: with the internal pull-down on, a line that still
// reads HIGH is being held at 3.3 V by the board's pull-up (i.e. connected + powered)
void checkLines() {
  pinMode(PIN_SDA, INPUT_PULLDOWN);
  pinMode(PIN_SCL, INPUT_PULLDOWN);
  delay(5);
  bool sda = digitalRead(PIN_SDA), scl = digitalRead(PIN_SCL);
  Serial.printf("Bus lines: SDA %s, SCL %s\r\n",
                sda ? "HIGH (OK)" : "LOW (not connected / no power)",
                scl ? "HIGH (OK)" : "LOW (not connected / no power)");
  pinMode(PIN_SDA, INPUT);
  pinMode(PIN_SCL, INPUT);
}

void scanBus() {
  Serial.print("I2C devices:");
  int n = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) { Serial.printf(" 0x%02X", a); n++; }
  }
  Serial.println(n ? "" : " none");
}

bool initImu() {
  scanBus();

  imuAddr = 0;
  for (uint8_t a : {0x69, 0x68}) {
    uint8_t id = readReg(a, REG_WHO_AM_I);
    if (id != 0xEE) {
      Serial.printf("WHO_AM_I @0x%02X = 0x%02X %s\r\n", a, id, id == 0xEA ? "-> ICM-20948 OK" : "-> not an ICM-20948");
      if (id == 0xEA) { imuAddr = a; break; }
    }
  }
  if (!imuAddr) return false;

  selectBank(0);
  writeReg(imuAddr, REG_PWR_MGMT_1, 0x80);     // reset
  delay(100);
  writeReg(imuAddr, REG_PWR_MGMT_1, 0x01);     // wake, auto clock
  delay(50);
  writeReg(imuAddr, REG_PWR_MGMT_2, 0x00);     // accel + gyro on

  selectBank(2);
  writeReg(imuAddr, B2_GYRO_SMPLRT_DIV, 0x00);
  writeReg(imuAddr, B2_GYRO_CONFIG_1, 0x19);   // +/-250 dps, DLPF ~51 Hz
  writeReg(imuAddr, B2_ACCEL_SMPLRT_DIV_2, 0x00);
  writeReg(imuAddr, B2_ACCEL_CONFIG, 0x19);    // +/-2 g, DLPF ~50 Hz
  selectBank(0);

  // Bypass: put the AK09916 directly on the ESP32's I2C bus
  writeReg(imuAddr, REG_USER_CTRL, 0x00);      // I2C master off
  writeReg(imuAddr, REG_INT_PIN_CFG, 0x02);    // BYPASS_EN
  delay(10);

  uint8_t wia = readReg(AK_ADDR, AK_WIA2);
  Serial.printf("AK09916 WIA2 = 0x%02X (expect 0x09)\r\n", wia);
  magOk = (wia == 0x09);
  if (magOk) {
    writeReg(AK_ADDR, AK_CNTL3, 0x01);         // soft reset
    delay(10);
    writeReg(AK_ADDR, AK_CNTL2, 0x08);         // continuous 100 Hz
    Serial.println("Magnetometer OK");
  } else {
    Serial.println("Magnetometer not found - continuing without heading");
  }
  return true;
}

bool readSample(Sample &s, bool applyCal = true) {
  uint8_t b[14];
  if (!readRegs(imuAddr, REG_ACCEL_XOUT_H, b, 14)) return false;
  s.ax = (int16_t)((b[0] << 8) | b[1]) / 16384.0f;
  s.ay = (int16_t)((b[2] << 8) | b[3]) / 16384.0f;
  s.az = (int16_t)((b[4] << 8) | b[5]) / 16384.0f;
  if (applyCal) {
    s.ax = (s.ax - cal.accOff[0]) / cal.accScale[0];
    s.ay = (s.ay - cal.accOff[1]) / cal.accScale[1];
    s.az = (s.az - cal.accOff[2]) / cal.accScale[2];
  }
  s.gx = (int16_t)((b[6] << 8) | b[7]) / 131.0f;
  s.gy = (int16_t)((b[8] << 8) | b[9]) / 131.0f;
  s.gz = (int16_t)((b[10] << 8) | b[11]) / 131.0f;
  s.temp = (int16_t)((b[12] << 8) | b[13]) / 333.87f + 21.0f;
  return true;
}

// Returns true when new data was read; output in uT, rotated into the accel frame
bool readMag(float m[3], bool applyCal = true) {
  uint8_t st1 = readReg(AK_ADDR, AK_ST1);
  if (st1 == 0xEE || !(st1 & 0x01)) return false;
  uint8_t b[8];                                 // HXL..HZH, TMPS, ST2 (reading ST2 ends the cycle)
  if (!readRegs(AK_ADDR, AK_HXL, b, 8)) return false;
  if (b[7] & 0x08) return false;                // magnetic overflow
  int16_t x = (b[1] << 8) | b[0], y = (b[3] << 8) | b[2], z = (b[5] << 8) | b[4];
  // AK09916 axes: X same as accel, Y and Z inverted
  m[0] =  x * 0.15f;
  m[1] = -y * 0.15f;
  m[2] = -z * 0.15f;
  if (applyCal) {
    for (int k = 0; k < 3; k++) m[k] = (m[k] - cal.magOff[k]) * cal.magScale[k];
  }
  return true;
}

void accelAngles(const Sample &s, float &r, float &p) {
  r = atan2f(s.ay, s.az) * RAD_TO_DEG;
  p = atan2f(-s.ax, sqrtf(s.ay * s.ay + s.az * s.az)) * RAD_TO_DEG;
}

float tiltCompensatedHeading(const float m[3]) {
  float r = roll * DEG_TO_RAD, p = pitch * DEG_TO_RAD;
  float xh = m[0] * cosf(p) + m[1] * sinf(r) * sinf(p) + m[2] * cosf(r) * sinf(p);
  float yh = m[1] * cosf(r) - m[2] * sinf(r);
  float h = atan2f(-yh, xh) * RAD_TO_DEG;
  return h < 0 ? h + 360 : h;
}

void calibrateGyro() {
  const int N = 1000;
  const float MAX_STDEV = 10.0f;      // deg/s; more than this means the board was moved
  Sample s;
  for (;;) {
    Serial.println("Calibrating gyro - keep the sensor still...");
    float sum[3] = {0, 0, 0}, sumSq[3] = {0, 0, 0};
    for (int i = 0; i < N; i++) {
      readSample(s);
      float g[3] = {s.gx, s.gy, s.gz};
      for (int k = 0; k < 3; k++) { sum[k] += g[k]; sumSq[k] += g[k] * g[k]; }
      delay(2);
    }
    float sd[3];
    bool still = true;
    for (int k = 0; k < 3; k++) {
      gyroBias[k] = sum[k] / N;
      sd[k] = sqrtf(fmaxf(sumSq[k] / N - gyroBias[k] * gyroBias[k], 0));
      still &= sd[k] < MAX_STDEV;
    }
    Serial.printf("Gyro noise [dps]: %.2f %.2f %.2f\r\n", sd[0], sd[1], sd[2]);
    if (still) {
      Serial.printf("Gyro bias [dps]: %.2f %.2f %.2f\r\n", gyroBias[0], gyroBias[1], gyroBias[2]);
      break;
    }
    Serial.println("Movement detected - retrying");
  }
  readSample(s);
  accelAngles(s, roll, pitch);
  yaw = 0;
  lastUpdateUs = micros();
}

const char AXIS[3] = {'X', 'Y', 'Z'};

void resetCal() {
  cal.magic = CAL_MAGIC;
  for (int k = 0; k < 3; k++) {
    cal.accOff[k] = 0; cal.accScale[k] = 1;
    cal.magOff[k] = 0; cal.magScale[k] = 1;
  }
  cal.accDone = cal.magDone = false;
}

void saveCal() {
  prefs.begin("icm20948", false);
  prefs.putBytes("cal", &cal, sizeof(cal));
  prefs.end();
  Serial.println("Calibration saved to flash");
}

void loadCal() {
  resetCal();
  prefs.begin("icm20948", true);
  Calibration c;
  if (prefs.getBytes("cal", &c, sizeof(c)) == sizeof(c) && c.magic == CAL_MAGIC) cal = c;
  prefs.end();
  Serial.printf("Saved calibration: accel %s, mag %s\r\n",
                cal.accDone ? "loaded" : "NOT done (send 'a')",
                cal.magDone ? "loaded" : "NOT done (send 'm')");
}

// Average raw (uncalibrated) accel over n samples; returns false if the board moved
bool stillAverage(float acc[3], int n = 200) {
  Sample s;
  float sum[3] = {0, 0, 0}, sumSq = 0;
  for (int i = 0; i < n; i++) {
    if (!readSample(s, false)) return false;
    sum[0] += s.ax; sum[1] += s.ay; sum[2] += s.az;
    float gx = s.gx - gyroBias[0], gy = s.gy - gyroBias[1], gz = s.gz - gyroBias[2];
    float g2 = gx * gx + gy * gy + gz * gz;
    if (g2 > sumSq) sumSq = g2;
    delay(2);
  }
  for (int k = 0; k < 3; k++) acc[k] = sum[k] / n;
  return sqrtf(sumSq) < 4.0f;          // peak rotation < 4 dps during the average
}

// 6-position calibration: each axis pointing up (+1 g) and down (-1 g)
void calibrateAccel() {
  float pos[3] = {0, 0, 0}, neg[3] = {0, 0, 0};
  bool havePos[3] = {false, false, false}, haveNeg[3] = {false, false, false};
  int captured = 0;
  Serial.println("\r\nAccel calibration: place the board still on each of its 6 faces.");
  Serial.println("Each face is captured automatically after ~1 s of no movement. Send 'q' to abort.");
  uint32_t lastHint = 0;
  while (captured < 6) {
    if (Serial.available() && Serial.read() == 'q') { Serial.println("Aborted"); return; }
    if (millis() - lastHint > 4000) {
      lastHint = millis();
      Serial.print("  Still needed:");
      for (int k = 0; k < 3; k++) {
        if (!havePos[k]) Serial.printf(" %c-up", AXIS[k]);
        if (!haveNeg[k]) Serial.printf(" %c-down", AXIS[k]);
      }
      Serial.println();
    }
    float a[3];
    if (!stillAverage(a, 150)) continue;
    // which axis carries gravity?
    int k = 0;
    for (int i = 1; i < 3; i++) if (fabsf(a[i]) > fabsf(a[k])) k = i;
    if (fabsf(a[k]) < 0.8f || fabsf(a[(k + 1) % 3]) > 0.25f || fabsf(a[(k + 2) % 3]) > 0.25f) continue;
    bool up = a[k] > 0;
    if ((up && havePos[k]) || (!up && haveNeg[k])) continue;
    float avg[3];
    if (!stillAverage(avg, 500)) continue;     // longer average for the actual reading
    if (up) { pos[k] = avg[k]; havePos[k] = true; } else { neg[k] = avg[k]; haveNeg[k] = true; }
    captured++;
    Serial.printf("  Captured %c-%s: %+.4f g  (%d/6)\r\n", AXIS[k], up ? "up" : "down", avg[k], captured);
  }
  for (int k = 0; k < 3; k++) {
    cal.accOff[k] = (pos[k] + neg[k]) / 2;
    cal.accScale[k] = (pos[k] - neg[k]) / 2;
  }
  cal.accDone = true;
  Serial.println("Accel calibration done:");
  for (int k = 0; k < 3; k++)
    Serial.printf("  %c: +1g reads %+.4f, -1g reads %+.4f -> offset %+.4f g, scale %.4f\r\n",
                  AXIS[k], pos[k], neg[k], cal.accOff[k], cal.accScale[k]);
  saveCal();
  calibrateGyro();                             // restart the filter with calibrated angles
}

// Hard-iron (offset) + soft-iron (per-axis scale) calibration from min/max while rotating
void calibrateMag() {
  if (!magOk) { Serial.println("No magnetometer"); return; }
  Serial.println("\r\nMag calibration: rotate the board slowly through ALL orientations for 20 s");
  Serial.println("(figure-8 motions, flip it over, roll it on every side). Keep away from metal/magnets.");
  float mn[3] = {1e9, 1e9, 1e9}, mx[3] = {-1e9, -1e9, -1e9}, m[3];
  uint32_t start = millis(), lastTick = 0;
  while (millis() - start < 20000) {
    if (readMag(m, false)) {
      for (int k = 0; k < 3; k++) { mn[k] = fminf(mn[k], m[k]); mx[k] = fmaxf(mx[k], m[k]); }
    }
    if (millis() - lastTick > 2000) {
      lastTick = millis();
      Serial.printf("  %2lus  range X %5.1f  Y %5.1f  Z %5.1f uT\r\n", (unsigned long)((millis() - start) / 1000),
                    mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]);
    }
    delay(10);
  }
  float range[3], avgRange = 0;
  for (int k = 0; k < 3; k++) { range[k] = mx[k] - mn[k]; avgRange += range[k] / 3; }
  for (int k = 0; k < 3; k++) {
    if (range[k] < 30) {
      Serial.printf("Not enough rotation on %c (range %.1f uT, need > 30) - calibration NOT saved, try again\r\n",
                    AXIS[k], range[k]);
      lastUpdateUs = micros();
      return;
    }
  }
  for (int k = 0; k < 3; k++) {
    cal.magOff[k] = (mx[k] + mn[k]) / 2;
    cal.magScale[k] = avgRange / range[k];
  }
  cal.magDone = true;
  Serial.println("Mag calibration done:");
  for (int k = 0; k < 3; k++)
    Serial.printf("  %c: min %+6.1f max %+6.1f -> offset %+6.1f uT, scale %.3f\r\n",
                  AXIS[k], mn[k], mx[k], cal.magOff[k], cal.magScale[k]);
  Serial.printf("  Earth field strength here ~ %.1f uT\r\n", avgRange / 2);
  saveCal();
  lastUpdateUs = micros();
}

void printAxisReport() {
  Sample s;
  float acc[3] = {0, 0, 0}, gyr[3] = {0, 0, 0}, mag[3] = {0, 0, 0}, m[3];
  const int N = 100;
  int magN = 0;
  for (int i = 0; i < N; i++) {
    readSample(s);
    acc[0] += s.ax / N; acc[1] += s.ay / N; acc[2] += s.az / N;
    gyr[0] += (s.gx - gyroBias[0]) / N; gyr[1] += (s.gy - gyroBias[1]) / N; gyr[2] += (s.gz - gyroBias[2]) / N;
    if (magOk && readMag(m)) { for (int k = 0; k < 3; k++) mag[k] += m[k]; magN++; }
    delay(5);
  }
  if (magN) for (int k = 0; k < 3; k++) mag[k] /= magN;

  Serial.println("\r\n================ AXIS REPORT ================");
  Serial.printf("Accel cal: %s   Mag cal: %s\r\n", cal.accDone ? "yes" : "NO", cal.magDone ? "yes" : "NO");
  Serial.println("Axis | Acc off(g) scale | Gyro bias(dps) | Mag off(uT) scale | Acc(g)  Gyro(dps)  Mag(uT)");
  for (int k = 0; k < 3; k++)
    Serial.printf("  %c  |  %+.4f  %.4f  |     %+6.2f     |  %+6.1f  %.3f  | %+5.2f   %+6.2f   %+6.1f\r\n",
                  AXIS[k], cal.accOff[k], cal.accScale[k], gyroBias[k],
                  cal.magOff[k], cal.magScale[k], acc[k], gyr[k], mag[k]);
  float g = sqrtf(acc[0] * acc[0] + acc[1] * acc[1] + acc[2] * acc[2]);
  int k = 0;
  for (int i = 1; i < 3; i++) if (fabsf(acc[i]) > fabsf(acc[k])) k = i;
  Serial.printf("|Acc| = %.3f g (ideal 1.000)   gravity along %c axis, %c points %s\r\n",
                g, AXIS[k], AXIS[k], acc[k] > 0 ? "UP" : "DOWN");
  if (magN) Serial.printf("|Mag| = %.1f uT (Earth: 25-65)   Heading %.1f deg\r\n",
                          sqrtf(mag[0] * mag[0] + mag[1] * mag[1] + mag[2] * mag[2]), tiltCompensatedHeading(mag));
  Serial.println("=============================================\r\n");
  lastUpdateUs = micros();
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\r\nICM-20948 I2C (SDA=21 SCL=22)");

  checkLines();
  Wire.begin(PIN_SDA, PIN_SCL, 400000);

  while (!initImu()) {
    Serial.println("ICM-20948 not found - check wiring, retrying in 2 s\r\n");
    delay(2000);
  }
  loadCal();
  calibrateGyro();
  printAxisReport();
  Serial.println("Send 'a' = accel cal, 'm' = mag cal, 'c' = gyro cal, 'p' = axis report, 'z' = zero yaw, 'r' = erase cal\r\n");
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'c') calibrateGyro();
    else if (c == 'a') calibrateAccel();
    else if (c == 'm') calibrateMag();
    else if (c == 'p') printAxisReport();
    else if (c == 'z') yaw = 0;
    else if (c == 'r') { resetCal(); saveCal(); Serial.println("Calibration erased"); }
  }

  uint32_t now = micros();
  if (now - lastUpdateUs < UPDATE_US) return;
  float dt = (now - lastUpdateUs) * 1e-6f;
  lastUpdateUs = now;

  Sample s;
  if (!readSample(s)) {
    Serial.println("I2C read failed");
    delay(500);
    return;
  }
  float gx = s.gx - gyroBias[0], gy = s.gy - gyroBias[1], gz = s.gz - gyroBias[2];

  float accRoll, accPitch;
  accelAngles(s, accRoll, accPitch);
  roll  = ALPHA * (roll + gx * dt)  + (1 - ALPHA) * accRoll;
  pitch = ALPHA * (pitch + gy * dt) + (1 - ALPHA) * accPitch;
  yaw  += gz * dt;   // gyro only: drifts slowly; use Heading for absolute direction
  if (yaw > 180) yaw -= 360;
  if (yaw < -180) yaw += 360;

  if (magOk) readMag(lastMag);

  if (millis() - lastPrintMs < PRINT_MS) return;
  lastPrintMs = millis();

  Serial.printf("Roll %6.1f Pitch %6.1f Yaw %6.1f | Acc[g] %5.2f %5.2f %5.2f | Gyro[dps] %6.1f %6.1f %6.1f | T %4.1fC",
                roll, pitch, yaw, s.ax, s.ay, s.az, gx, gy, gz, s.temp);
  if (magOk) {
    Serial.printf(" | Mag[uT] %6.1f %6.1f %6.1f | Heading %5.1f",
                  lastMag[0], lastMag[1], lastMag[2], tiltCompensatedHeading(lastMag));
  }
  Serial.println();
}
