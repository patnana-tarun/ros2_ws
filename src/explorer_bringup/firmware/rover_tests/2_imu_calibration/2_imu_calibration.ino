/*
  Explorer Rover - Test 2: ICM-20948 IMU check + calibration
  -----------------------------------------------------------
  Wiring (Qwiic -> ESP32):  3.3V, GND, SDA -> GPIO 21, SCL -> GPIO 22
  Library: "SparkFun 9DoF IMU Breakout - ICM 20948" (Arduino Library Manager)

  Serial Monitor 115200. Keys:
    c = gyro + accel calibration (robot STILL and FLAT, takes ~5 s)
    m = magnetometer calibration (rotate robot slowly in all directions, 20 s)
    t = 90 deg turn test (rotate robot by hand, watch yaw)
    r = reset yaw to 0
    p = print raw data stream on/off

  At the end it prints lines to paste into sketches 5, 6 and 7.
*/
#include <Wire.h>
#include "ICM_20948.h"

ICM_20948_I2C imu;
const int SDA_PIN = 21, SCL_PIN = 22;
const int AD0_VAL = 1;          // SparkFun default address 0x69. Use 0 if scanner shows 0x68

float gyroBias[3]  = {0, 0, 0}; // dps
float accelBias[3] = {0, 0, 0}; // mg
float magOffset[3] = {0, 0, 0}; // uT

float yawDeg = 0;
unsigned long lastUs = 0;
bool streamRaw = false;
bool turnTest = false;

void i2cScan() {
  Serial.println("I2C scan:");
  int found = 0;
  for (byte a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) { Serial.printf("  device at 0x%02X\n", a); found++; }
  }
  if (!found) Serial.println("  nothing found -> check 3.3V, GND, SDA 21, SCL 22");
}

bool readImu() {
  if (!imu.dataReady()) return false;
  imu.getAGMT();
  return true;
}

void calibrateGyroAccel() {
  Serial.println("\nKeep the robot STILL and FLAT... starting in 2 s");
  delay(2000);
  const int N = 1000;
  double g[3] = {0}, a[3] = {0};
  int n = 0;
  while (n < N) {
    if (readImu()) {
      g[0] += imu.gyrX(); g[1] += imu.gyrY(); g[2] += imu.gyrZ();
      a[0] += imu.accX(); a[1] += imu.accY(); a[2] += imu.accZ();
      n++;
    }
  }
  for (int i = 0; i < 3; i++) { gyroBias[i] = g[i] / N; }
  accelBias[0] = a[0] / N;
  accelBias[1] = a[1] / N;
  accelBias[2] = a[2] / N - 1000.0;   // Z should read +1 g (1000 mg) when flat
  yawDeg = 0;

  Serial.println("Gyro + accel calibration done.");
  float noise = 0;
  // quick noise check
  for (int i = 0; i < 200;) {
    if (readImu()) { noise = max(noise, fabsf(imu.gyrZ() - gyroBias[2])); i++; }
  }
  Serial.printf("Gyro Z noise after bias removal: %.2f dps (good if < 0.5)\n", noise);
  printPasteLines();
}

void calibrateMag() {
  Serial.println("\nRotate the robot slowly in ALL directions for 20 s...");
  float mn[3] = { 1e9,  1e9,  1e9};
  float mx[3] = {-1e9, -1e9, -1e9};
  unsigned long t0 = millis();
  while (millis() - t0 < 20000) {
    if (readImu()) {
      float m[3] = {imu.magX(), imu.magY(), imu.magZ()};
      for (int i = 0; i < 3; i++) { mn[i] = min(mn[i], m[i]); mx[i] = max(mx[i], m[i]); }
    }
  }
  for (int i = 0; i < 3; i++) magOffset[i] = (mx[i] + mn[i]) / 2.0;
  Serial.println("Mag calibration done (optional; indoors near motors it is unreliable).");
  printPasteLines();
}

void printPasteLines() {
  Serial.println("\n----- paste into sketches 5, 6, 7 -----");
  Serial.printf("float GYRO_Z_BIAS = %.4f;\n", gyroBias[2]);
  Serial.printf("float GYRO_X_BIAS = %.4f, GYRO_Y_BIAS = %.4f;\n", gyroBias[0], gyroBias[1]);
  Serial.printf("float ACCEL_BIAS[3] = {%.2f, %.2f, %.2f};\n", accelBias[0], accelBias[1], accelBias[2]);
  Serial.printf("float MAG_OFFSET[3] = {%.2f, %.2f, %.2f};\n", magOffset[0], magOffset[1], magOffset[2]);
  Serial.println("----------------------------------------\n");
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);
  i2cScan();

  while (true) {
    imu.begin(Wire, AD0_VAL);
    if (imu.status == ICM_20948_Stat_Ok) break;
    Serial.printf("IMU not found (%s). Retrying...\n", imu.statusString());
    delay(1000);
  }

  // Gyro range 500 dps (robot spins well below this), accel 2 g
  ICM_20948_fss_t fss;
  fss.a = gpm2;
  fss.g = dps500;
  imu.setFullScale((ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr), fss);

  // Low-pass filter to cut motor vibration noise
  ICM_20948_dlpcfg_t dlp;
  dlp.a = acc_d23bw9_n34bw4;
  dlp.g = gyr_d23bw9_n35bw9;
  imu.setDLPFcfg((ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr), dlp);
  imu.enableDLPF(ICM_20948_Internal_Acc, true);
  imu.enableDLPF(ICM_20948_Internal_Gyr, true);

  Serial.println("\nICM-20948 OK. Keys: c=calibrate, m=mag cal, t=90deg test, r=reset yaw, p=raw stream");
  lastUs = micros();
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'c') calibrateGyroAccel();
    else if (c == 'm') calibrateMag();
    else if (c == 'r') { yawDeg = 0; Serial.println("Yaw reset"); }
    else if (c == 'p') streamRaw = !streamRaw;
    else if (c == 't') {
      turnTest = !turnTest; yawDeg = 0;
      Serial.println(turnTest ? "Turn test ON: rotate robot 90 deg by hand" : "Turn test OFF");
    }
  }

  if (readImu()) {
    unsigned long now = micros();
    float dt = (now - lastUs) / 1e6;
    lastUs = now;
    float gz = imu.gyrZ() - gyroBias[2];
    if (fabsf(gz) < 0.3) gz = 0;          // small deadband stops slow drift at rest
    yawDeg += gz * dt;

    static unsigned long lastPrint = 0;
    if (millis() - lastPrint > 200) {
      lastPrint = millis();
      if (streamRaw) {
        Serial.printf("acc[mg] %7.1f %7.1f %7.1f | gyr[dps] %6.2f %6.2f %6.2f | mag[uT] %6.1f %6.1f %6.1f\n",
          imu.accX() - accelBias[0], imu.accY() - accelBias[1], imu.accZ() - accelBias[2],
          imu.gyrX() - gyroBias[0], imu.gyrY() - gyroBias[1], gz,
          imu.magX() - magOffset[0], imu.magY() - magOffset[1], imu.magZ() - magOffset[2]);
      }
      if (turnTest) Serial.printf("Yaw = %7.2f deg\n", yawDeg);
    }
  }
}
