/*
  Explorer Rover - Test 3: Encoders only (turn wheels BY HAND, motors off)
  ------------------------------------------------------------------------
  4 encoders on the corner wheels:
    Left front  A=16 B=17      Left rear  A=18 B=19
    Right front A=23 B=34      Right rear A=35 B=32
  GPIO 34 and 35 have no internal pull-up: add 10k to 3.3V if your
  encoder board has no pull-ups of its own.

  Serial Monitor 115200. Keys:
    r = reset all counts
    m = measure ticks per wheel turn (press m, turn LEFT FRONT wheel
        exactly 10 turns forward, press m again)
    p = printing on/off
*/

// true = encoders have A and B outputs (quadrature). false = A only.
const bool ENC_QUADRATURE = true;

const int ENC_A[4] = {16, 18, 23, 35};
const int ENC_B[4] = {17, 19, 34, 32};
const char* ENC_NAME[4] = {"LF", "LR", "RF", "RR"};
// If a wheel counts NEGATIVE when turned forward, flip its sign here.
const int ENC_SIGN[4] = {1, 1, -1, -1};   // right side usually mirrored

volatile long encCount[4] = {0, 0, 0, 0};

void IRAM_ATTR isr0() { encCount[0] += (!ENC_QUADRATURE || digitalRead(ENC_B[0])) ? 1 : -1; }
void IRAM_ATTR isr1() { encCount[1] += (!ENC_QUADRATURE || digitalRead(ENC_B[1])) ? 1 : -1; }
void IRAM_ATTR isr2() { encCount[2] += (!ENC_QUADRATURE || digitalRead(ENC_B[2])) ? 1 : -1; }
void IRAM_ATTR isr3() { encCount[3] += (!ENC_QUADRATURE || digitalRead(ENC_B[3])) ? 1 : -1; }
void (*isrs[4])() = {isr0, isr1, isr2, isr3};

const int STBY = 4;   // keep motors disabled during this test

long readCount(int i) {
  noInterrupts();
  long c = encCount[i];
  interrupts();
  return c * ENC_SIGN[i];
}

void resetCounts() {
  noInterrupts();
  for (int i = 0; i < 4; i++) encCount[i] = 0;
  interrupts();
}

bool printing = true;
bool measuring = false;

void setup() {
  Serial.begin(115200);
  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, LOW);

  for (int i = 0; i < 4; i++) {
    pinMode(ENC_A[i], INPUT_PULLUP);   // pull-up ignored on 34/35
    if (ENC_QUADRATURE) pinMode(ENC_B[i], INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(ENC_A[i]), isrs[i], RISING);
  }
  Serial.println("\nEncoder test. Turn wheels by hand. r=reset, m=measure, p=print on/off");
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'r') { resetCounts(); Serial.println("Counts reset"); }
    else if (c == 'p') printing = !printing;
    else if (c == 'm') {
      if (!measuring) {
        resetCounts(); measuring = true; printing = false;
        Serial.println("Turn LEFT FRONT wheel exactly 10 turns forward, then press m");
      } else {
        measuring = false; printing = true;
        long ticks = readCount(0);
        Serial.printf("Ticks for 10 turns = %ld  ->  TICKS_PER_REV = %.1f\n", ticks, ticks / 10.0);
        Serial.println("Paste that value into sketches 4, 6 and 7.");
      }
    }
  }

  static unsigned long last = 0;
  if (printing && millis() - last > 200) {
    last = millis();
    Serial.printf("LF %7ld | LR %7ld | RF %7ld | RR %7ld\n",
                  readCount(0), readCount(1), readCount(2), readCount(3));
  }
}
