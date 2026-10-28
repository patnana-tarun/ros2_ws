/*
  Explorer Rover - Test 5: Motors + IMU (heading hold and exact turns)
  --------------------------------------------------------------------
  Uses the gyro to:
    - drive straight (corrects drift between left and right sides)
    - turn by an exact angle (90 deg)
  No encoders here, so speed is open-loop PWM.

  Before running: paste GYRO_Z_BIAS from test 2.

  Serial Monitor 115200. Keys:
    w = drive straight forward with heading hold
    s = drive straight reverse with heading hold
    l = turn left 90 deg       r = turn right 90 deg
    x = stop                   z = reset heading to 0
    + / - = speed up / down    k / j = heading gain up / down
  Watchdog: driving stops 3 s after the last key (turns finish on their own).
*/
#include <Wire.h>
#include "ICM_20948.h"

// ---------- Motor pins ----------
const int L_PWM = 25, L_IN1 = 26, L_IN2 = 27;
const int R_PWM = 33, R_IN1 = 14, R_IN2 = 13;
const int STBY  = 4;
const bool INVERT_LEFT = false, INVERT_RIGHT = false;
const int PWM_FREQ = 20000, PWM_RES = 8, MAX_DUTY = 191;

// ---------- IMU ----------
ICM_20948_I2C imu;
const int AD0_VAL = 1;
float GYRO_Z_BIAS = 0.0;            // <-- paste from test 2

// ---------- State ----------
enum Mode { IDLE, STRAIGHT, TURNING };
Mode mode = IDLE;
int baseDuty = 100;
int dir = 1;                         // 1 forward, -1 reverse
float Kh = 6.0;                      // PWM per degree of heading error
float yaw = 0, holdYaw = 0, turnTarget = 0;
unsigned long lastUs = 0, lastCmdMs = 0;

void driveSide(int pwmPin, int in1, int in2, int speed, bool inv) {
  if (inv) speed = -speed;
  speed = constrain(speed, -MAX_DUTY, MAX_DUTY);
  if (speed > 0)      { digitalWrite(in1, HIGH); digitalWrite(in2, LOW);  }
  else if (speed < 0) { digitalWrite(in1, LOW);  digitalWrite(in2, HIGH); }
  else                { digitalWrite(in1, HIGH); digitalWrite(in2, HIGH); }
  ledcWrite(pwmPin, abs(speed));
}
void drive(int l, int r) {
  digitalWrite(STBY, (l || r) ? HIGH : LOW);
  driveSide(L_PWM, L_IN1, L_IN2, l, INVERT_LEFT);
  driveSide(R_PWM, R_IN1, R_IN2, r, INVERT_RIGHT);
}
void stopAll() { drive(0, 0); mode = IDLE; }

void updateYaw() {
  if (!imu.dataReady()) return;
  imu.getAGMT();
  unsigned long now = micros();
  float dt = (now - lastUs) / 1e6;
  lastUs = now;
  float gz = imu.gyrZ() - GYRO_Z_BIAS;
  if (fabsf(gz) < 0.3) gz = 0;
  yaw += gz * dt;                    // + = counter-clockwise (left)
}

void setup() {
  Serial.begin(115200);
  pinMode(STBY, OUTPUT); digitalWrite(STBY, LOW);
  pinMode(L_IN1, OUTPUT); pinMode(L_IN2, OUTPUT);
  pinMode(R_IN1, OUTPUT); pinMode(R_IN2, OUTPUT);
  ledcAttach(L_PWM, PWM_FREQ, PWM_RES);
  ledcAttach(R_PWM, PWM_FREQ, PWM_RES);

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

  lastUs = micros();
  Serial.println("\nHeading test. w/s straight, l/r turn 90, x stop, z zero, +/- speed, k/j gain");
}

void loop() {
  updateYaw();

  if (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') return;
    lastCmdMs = millis();
    switch (c) {
      case 'w': dir =  1; holdYaw = yaw; mode = STRAIGHT; break;
      case 's': dir = -1; holdYaw = yaw; mode = STRAIGHT; break;
      case 'l': turnTarget = yaw + 90; mode = TURNING; break;
      case 'r': turnTarget = yaw - 90; mode = TURNING; break;
      case 'x': stopAll(); break;
      case 'z': yaw = 0; holdYaw = 0; break;
      case '+': baseDuty = min(baseDuty + 15, MAX_DUTY); break;
      case '-': baseDuty = max(baseDuty - 15, 40); break;
      case 'k': Kh += 1; break;
      case 'j': Kh = max(0.0f, Kh - 1); break;
    }
    Serial.printf("cmd %c | duty=%d Kh=%.1f yaw=%.1f\n", c, baseDuty, Kh, yaw);
  }

  if (mode == STRAIGHT) {
    float err = holdYaw - yaw;                 // + means robot drifted right
    int corr = (int)(Kh * err);
    // positive corr -> turn left -> slow left, speed right
    drive(dir * baseDuty - corr, dir * baseDuty + corr);
    if (millis() - lastCmdMs > 3000) { stopAll(); Serial.println("Timeout -> stopped"); }
  }
  else if (mode == TURNING) {
    float err = turnTarget - yaw;
    if (fabsf(err) < 2.0) {
      stopAll();
      Serial.printf("Turn done. yaw=%.1f (target %.1f)\n", yaw, turnTarget);
    } else {
      int duty = constrain((int)(fabsf(err) * 3), 70, baseDuty);   // slow down near target
      int s = (err > 0) ? 1 : -1;                                   // + = turn left
      drive(-s * duty, s * duty);
    }
  }

  static unsigned long lp = 0;
  if (mode != IDLE && millis() - lp > 200) {
    lp = millis();
    Serial.printf("yaw=%7.2f\n", yaw);
  }
}
