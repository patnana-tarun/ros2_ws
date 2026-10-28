/*
  Explorer Rover - Test 4: Motors + Encoders (closed-loop speed, PID)
  -------------------------------------------------------------------
  Same motor and encoder pins as tests 1 and 3.
  Each side's speed = average of its two encoders (front + rear).
  PI controller keeps each side at the target speed.

  Before running: set TICKS_PER_REV from test 3.

  Serial Monitor 115200. Keys:
    w / s = forward / reverse at target speed
    a / d = spin left / right
    x     = stop
    + / - = target speed up / down (0.05 m/s steps)
    k / l = Kp up / down       i / o = Ki up / down
  Watchdog: stops if no key for 3 s.
  Output: target, measured left/right speed (m/s), PWM, slip flag.
*/

// ---------- Motor pins ----------
const int L_PWM = 25, L_IN1 = 26, L_IN2 = 27;
const int R_PWM = 33, R_IN1 = 14, R_IN2 = 13;
const int STBY  = 4;
const bool INVERT_LEFT = false, INVERT_RIGHT = false;
const int PWM_FREQ = 20000, PWM_RES = 8, MAX_DUTY = 191;

// ---------- Encoder pins ----------
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

// ---------- Robot geometry ----------
float TICKS_PER_REV = 0;               // <-- SET from test 3 (e.g. 390)
const float WHEEL_DIAM_M = 0.065;
const float M_PER_TICK_BASE = PI * WHEEL_DIAM_M;

// ---------- Control ----------
const float LOOP_HZ = 50.0;
float Kp = 300.0, Ki = 800.0;          // PWM per (m/s) error; tune with k/l/i/o
float KF = 400.0;                      // feed-forward: rough PWM per m/s
float targetSpeed = 0.15;              // m/s
float tgtL = 0, tgtR = 0;
float intL = 0, intR = 0;
long prev[4] = {0, 0, 0, 0};
unsigned long lastCmdMs = 0, lastLoopMs = 0;
int pwmL = 0, pwmR = 0;

long readCount(int i) { noInterrupts(); long c = encCount[i]; interrupts(); return c * ENC_SIGN[i]; }

void driveSide(int pwmPin, int in1, int in2, int speed, bool inv) {
  if (inv) speed = -speed;
  speed = constrain(speed, -MAX_DUTY, MAX_DUTY);
  if (speed > 0)      { digitalWrite(in1, HIGH); digitalWrite(in2, LOW);  }
  else if (speed < 0) { digitalWrite(in1, LOW);  digitalWrite(in2, HIGH); }
  else                { digitalWrite(in1, HIGH); digitalWrite(in2, HIGH); }
  ledcWrite(pwmPin, abs(speed));
}

void setTargets(float l, float r) {
  tgtL = l; tgtR = r;
  intL = intR = 0;
  digitalWrite(STBY, (l != 0 || r != 0) ? HIGH : LOW);
}

int pi(float tgt, float meas, float &integ, float dt) {
  if (tgt == 0) { integ = 0; return 0; }
  float err = tgt - meas;
  integ += err * dt;
  integ = constrain(integ, -0.3, 0.3);            // anti-windup
  return (int)(KF * tgt + Kp * err + Ki * integ);
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
  if (TICKS_PER_REV <= 0) {
    Serial.println("Set TICKS_PER_REV from test 3 first!");
    while (true) delay(1000);
  }
  Serial.println("\nPID test. w/s/a/d/x, +/-, k/l (Kp), i/o (Ki)");
  lastLoopMs = millis();
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') return;
    lastCmdMs = millis();
    float v = targetSpeed;
    switch (c) {
      case 'w': setTargets( v,  v); break;
      case 's': setTargets(-v, -v); break;
      case 'a': setTargets(-v,  v); break;
      case 'd': setTargets( v, -v); break;
      case 'x': setTargets(0, 0); break;
      case '+': targetSpeed = min(targetSpeed + 0.05f, 0.6f); break;
      case '-': targetSpeed = max(targetSpeed - 0.05f, 0.05f); break;
      case 'k': Kp += 50; break;
      case 'l': Kp = max(0.0f, Kp - 50); break;
      case 'i': Ki += 100; break;
      case 'o': Ki = max(0.0f, Ki - 100); break;
    }
    Serial.printf("target=%.2f m/s  Kp=%.0f Ki=%.0f\n", targetSpeed, Kp, Ki);
  }

  if ((tgtL != 0 || tgtR != 0) && millis() - lastCmdMs > 3000) {
    setTargets(0, 0);
    Serial.println("Timeout -> stopped");
  }

  unsigned long now = millis();
  if (now - lastLoopMs >= 1000 / LOOP_HZ) {
    float dt = (now - lastLoopMs) / 1000.0;
    lastLoopMs = now;

    long c[4]; float d[4];
    for (int i = 0; i < 4; i++) {
      c[i] = readCount(i);
      d[i] = c[i] - prev[i];
      prev[i] = c[i];
    }
    // Single-channel encoders can't tell direction: take it from the command
    if (!ENC_QUADRATURE) {
      float sL = (tgtL >= 0) ? 1 : -1, sR = (tgtR >= 0) ? 1 : -1;
      d[0] = fabsf(d[0]) * sL; d[1] = fabsf(d[1]) * sL;
      d[2] = fabsf(d[2]) * sR; d[3] = fabsf(d[3]) * sR;
    }
    float mpt = M_PER_TICK_BASE / TICKS_PER_REV;
    float vLF = d[0] * mpt / dt, vLR = d[1] * mpt / dt;
    float vRF = d[2] * mpt / dt, vRR = d[3] * mpt / dt;
    float vL = (vLF + vLR) / 2, vR = (vRF + vRR) / 2;

    pwmL = pi(tgtL, vL, intL, dt);
    pwmR = pi(tgtR, vR, intR, dt);
    driveSide(L_PWM, L_IN1, L_IN2, pwmL, INVERT_LEFT);
    driveSide(R_PWM, R_IN1, R_IN2, pwmR, INVERT_RIGHT);

    // Slip: front and rear on the same side disagree by > 30%
    bool slipL = fabsf(vLF - vLR) > 0.3 * max(fabsf(vL), 0.05f);
    bool slipR = fabsf(vRF - vRR) > 0.3 * max(fabsf(vR), 0.05f);

    static int n = 0;
    if (++n >= 10) {     // print at 5 Hz
      n = 0;
      Serial.printf("tgt L%+.2f R%+.2f | meas L%+.2f R%+.2f | pwm L%4d R%4d %s%s\n",
                    tgtL, tgtR, vL, vR, pwmL, pwmR, slipL ? "SLIP-L " : "", slipR ? "SLIP-R" : "");
    }
  }
}
