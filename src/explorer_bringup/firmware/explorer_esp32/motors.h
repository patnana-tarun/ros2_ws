// TB6612FNG drive: one PWM + two direction pins per side, shared STBY.
#pragma once
#include "config.h"

namespace motors {

inline void side(int pwmPin, int in1, int in2, int duty, bool invert) {
  if (invert) duty = -duty;
  duty = constrain(duty, -MAX_DUTY, MAX_DUTY);
  if (duty > 0)      { digitalWrite(in1, HIGH); digitalWrite(in2, LOW);  }
  else if (duty < 0) { digitalWrite(in1, LOW);  digitalWrite(in2, HIGH); }
  else               { digitalWrite(in1, HIGH); digitalWrite(in2, HIGH); }   // brake
  ledcWrite(pwmPin, abs(duty));
}

// duty -MAX_DUTY..MAX_DUTY per side; both 0 brakes, then puts the drivers in standby
inline void set(int left, int right) {
  digitalWrite(STBY, (left || right) ? HIGH : LOW);
  side(L_PWM, L_IN1, L_IN2, left, INVERT_LEFT);
  side(R_PWM, R_IN1, R_IN2, right, INVERT_RIGHT);
}

inline void begin() {
  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, LOW);
  for (int p : {L_IN1, L_IN2, R_IN1, R_IN2}) pinMode(p, OUTPUT);
  ledcAttach(L_PWM, PWM_FREQ, PWM_RES);      // ESP32 Arduino core 3.x
  ledcAttach(R_PWM, PWM_FREQ, PWM_RES);
  set(0, 0);
}

}  // namespace motors
