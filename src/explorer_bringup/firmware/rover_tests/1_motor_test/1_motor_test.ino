/*
  Explorer Rover - Motor Driver Test (ESP32 + 3x TB6612FNG)
  ----------------------------------------------------------
  Motor wiring (as built):
    Driver 1: AO = Left middle,  BO = Left front
    Driver 2: AO = Left rear,    BO = Right rear
    Driver 3: AO = Right front,  BO = Right middle  (or swapped - doesn't matter)

  Signal wiring (shared per SIDE, not per A/B):
    LEFT group  = Driver1 A, Driver1 B, Driver2 A
    RIGHT group = Driver2 B, Driver3 A, Driver3 B

    ESP32 25 -> D1 PWMA, D1 PWMB, D2 PWMA      (left speed)
    ESP32 26 -> D1 AIN1, D1 BIN1, D2 AIN1      (left dir 1)
    ESP32 27 -> D1 AIN2, D1 BIN2, D2 AIN2      (left dir 2)
    ESP32 33 -> D2 PWMB, D3 PWMA, D3 PWMB      (right speed)
    ESP32 14 -> D2 BIN1, D3 AIN1, D3 BIN1      (right dir 1)
    ESP32 13 -> D2 BIN2, D3 AIN2, D3 BIN2      (right dir 2)
    ESP32 4  -> STBY on all 3 drivers (+ 10k to GND)

  Needs ESP32 Arduino core 3.x (uses ledcAttach / ledcWrite(pin, duty)).

  Serial Monitor at 115200, send one letter:
    w = forward      s = reverse
    a = spin left    d = spin right
    q = left side only forward    e = right side only forward
    x = stop (brake)
    + = speed up     - = speed down
    t = run automatic test sequence
  Safety: motors stop by themselves if no command for 3 s.
*/

// ---------- Pins (change here if your wiring differs) ----------
const int L_PWM = 25, L_IN1 = 26, L_IN2 = 27;
const int R_PWM = 33, R_IN1 = 14, R_IN2 = 13;
const int STBY  = 4;

// ---------- Direction fix ----------
// If one whole side spins backwards on 'w', set its flag to true.
const bool INVERT_LEFT  = false;
const bool INVERT_RIGHT = false;

// ---------- PWM settings ----------
const int PWM_FREQ = 20000;   // 20 kHz, silent
const int PWM_RES  = 8;       // 0..255
const int MAX_DUTY = 191;     // ~75%: motors rated 9 V, pack up to 12.6 V
const int STEP     = 20;

int speedDuty = 80;           // start slow (~30%)
unsigned long lastCmdMs = 0;
const unsigned long CMD_TIMEOUT_MS = 3000;
bool moving = false;

// speed: -255..255 (sign = direction)
void driveSide(int pwmPin, int in1, int in2, int speed, bool invert) {
  if (invert) speed = -speed;
  speed = constrain(speed, -MAX_DUTY, MAX_DUTY);
  if (speed > 0)      { digitalWrite(in1, HIGH); digitalWrite(in2, LOW);  }
  else if (speed < 0) { digitalWrite(in1, LOW);  digitalWrite(in2, HIGH); }
  else                { digitalWrite(in1, HIGH); digitalWrite(in2, HIGH); } // brake
  ledcWrite(pwmPin, abs(speed));
}

void drive(int left, int right) {
  digitalWrite(STBY, HIGH);
  driveSide(L_PWM, L_IN1, L_IN2, left,  INVERT_LEFT);
  driveSide(R_PWM, R_IN1, R_IN2, right, INVERT_RIGHT);
  moving = (left != 0 || right != 0);
}

void stopAll() {
  drive(0, 0);              // brake
  digitalWrite(STBY, LOW);  // then disable drivers
  moving = false;
}

void runStep(const char* name, int l, int r, int ms) {
  Serial.printf("  %-22s L=%4d R=%4d\n", name, l, r);
  drive(l, r);
  delay(ms);
  stopAll();
  delay(700);
}

void autoTest() {
  int v = speedDuty;
  Serial.println("Auto test (wheels off the ground!)");
  runStep("Left side forward",  v, 0, 2000);
  runStep("Right side forward", 0, v, 2000);
  runStep("Both forward",       v, v, 2000);
  runStep("Both reverse",      -v, -v, 2000);
  runStep("Spin left",         -v, v, 2000);
  runStep("Spin right",         v, -v, 2000);
  Serial.println("Auto test done.");
}

void setup() {
  Serial.begin(115200);

  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, LOW);  // motors off while setting up

  pinMode(L_IN1, OUTPUT); pinMode(L_IN2, OUTPUT);
  pinMode(R_IN1, OUTPUT); pinMode(R_IN2, OUTPUT);

  ledcAttach(L_PWM, PWM_FREQ, PWM_RES);
  ledcAttach(R_PWM, PWM_FREQ, PWM_RES);

  stopAll();
  Serial.println("\nMotor test ready. w/s/a/d/q/e/x, +/-, t");
  Serial.printf("Speed = %d / %d\n", speedDuty, MAX_DUTY);
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') return;
    lastCmdMs = millis();

    switch (c) {
      case 'w': drive( speedDuty,  speedDuty); Serial.println("Forward");    break;
      case 's': drive(-speedDuty, -speedDuty); Serial.println("Reverse");    break;
      case 'a': drive(-speedDuty,  speedDuty); Serial.println("Spin left");  break;
      case 'd': drive( speedDuty, -speedDuty); Serial.println("Spin right"); break;
      case 'q': drive( speedDuty, 0);          Serial.println("Left only");  break;
      case 'e': drive(0,  speedDuty);          Serial.println("Right only"); break;
      case 'x': stopAll();                     Serial.println("Stop");       break;
      case '+': speedDuty = min(speedDuty + STEP, MAX_DUTY);
                Serial.printf("Speed = %d\n", speedDuty); break;
      case '-': speedDuty = max(speedDuty - STEP, 0);
                Serial.printf("Speed = %d\n", speedDuty); break;
      case 't': autoTest(); break;
      default:  Serial.println("Unknown key"); break;
    }
  }

  // Safety watchdog: stop if no command for 3 s
  if (moving && millis() - lastCmdMs > CMD_TIMEOUT_MS) {
    stopAll();
    Serial.println("Timeout -> stopped");
  }
}
