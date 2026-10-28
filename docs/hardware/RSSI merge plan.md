---
tags: [concept]
---
# RSSI merge plan

**Not started** (the user's order: sensors first, RSSI later). Goal: the controller ESP32 also
measures the RSSI of one mesh node, so the rover itself can decide when to drop a relay
([[Relay placement protocol]]). Today the sniffer is a separate sketch
(`firmware/rssi_sniffer/`) logged on a laptop.

## Why one ESP32 can do both
The sniffer uses the Wi-Fi radio in promiscuous mode on channel 1 and a small callback on
core 0; the controller uses core 1, hardware PWM and interrupts. The link to the Pi is USB, so
the radio stays free for sniffing.

## Steps
1. New `firmware/explorer_esp32/rssi.h` from `rssi_sniffer.ino`: Wi-Fi in station mode,
   promiscuous filter (management + data), the callback that keeps only frames from the target
   MAC (address 2 = transmitter) and adds their RSSI to counters under a spinlock, the
   median-of-3 + EMA (α 0.35) filter. Keep the callback tiny; all maths in `loop()`.
2. Once per second an `R` line ([[Serial protocol]], "Adding a line type"), same columns as the
   sniffer's CSV: `R,<mac>,<channel>,<samples>,<last>,<avg>,<weakest>,<strongest>,<filtered>*HH`.
3. Commands `M,<mac>` (target) and `C,<channel>` from the Pi.
4. `esp32_bridge`: parameters `rssi_target_mac`, `rssi_channel` (sent at connect), publishes
   the `R` lines on a new topic (add it to [[Topics]]) and can append the sniffer's CSV format,
   so the field-test analysis scripts keep working.
5. `fake_robot` sends `R` lines; `hw_selftest` checks them.
6. Test that motors and Wi-Fi together don't disturb the speed loop: `esp32_check` timing with
   sniffing on, driving.

The target MAC is the **physical** Wi-Fi MAC (wlan0) of the node to listen to, not bat0's.
