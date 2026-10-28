// Four wheel encoders, counted on the rising edge of A (direction from B when quadrature).
#pragma once
#include "config.h"

namespace encoders {

constexpr float M_PER_TICK = TICKS_PER_REV > 0 ? PI * WHEEL_DIAM_M / TICKS_PER_REV : 0;

volatile int32_t raw[4] = {0, 0, 0, 0};
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
int32_t last[4] = {0, 0, 0, 0};
double total[4] = {0, 0, 0, 0};             // signed travel since boot, m

void IRAM_ATTR count(int i) {
  portENTER_CRITICAL_ISR(&mux);
  raw[i] += (!ENC_QUADRATURE || digitalRead(ENC_B[i])) ? 1 : -1;
  portEXIT_CRITICAL_ISR(&mux);
}
void IRAM_ATTR isr0() { count(0); }
void IRAM_ATTR isr1() { count(1); }
void IRAM_ATTR isr2() { count(2); }
void IRAM_ATTR isr3() { count(3); }

inline void begin() {
  void (*isrs[4])() = {isr0, isr1, isr2, isr3};
  for (int i = 0; i < 4; i++) {
    pinMode(ENC_A[i], INPUT_PULLUP);
    if (ENC_QUADRATURE) pinMode(ENC_B[i], INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(ENC_A[i]), isrs[i], RISING);
  }
}

// Travel of each wheel (m) since the last call. Single-channel encoders can't sense
// direction, so they take the sign of the side's target (dirL/dirR = +1 or -1).
inline void step(float d[4], int dirL, int dirR) {
  int32_t now[4];
  portENTER_CRITICAL(&mux);
  for (int i = 0; i < 4; i++) now[i] = raw[i];
  portEXIT_CRITICAL(&mux);
  for (int i = 0; i < 4; i++) {
    int32_t ticks = (now[i] - last[i]) * ENC_SIGN[i];
    last[i] = now[i];
    if (!ENC_QUADRATURE) ticks = abs(ticks) * (i < 2 ? dirL : dirR);
    d[i] = ticks * M_PER_TICK;
    total[i] += d[i];
  }
}

}  // namespace encoders
