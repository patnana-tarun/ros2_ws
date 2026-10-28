#!/usr/bin/env python3
"""Save the ESP32 RSSI sniffer output to a CSV file with date and HH:MM:SS time columns.

Rows are always appended to OUTPUT; existing data is never overwritten.

Usage:
    python3 rssi_csv_logger.py [PORT] [TARGET_MAC] [OUTPUT_CSV]
    python3 rssi_csv_logger.py /dev/ttyUSB0 d8:3a:dd:13:54:64 rssi_log.csv

Close the Arduino Serial Monitor first: only one program can use the port.
Stop logging with Ctrl+C.
"""

import csv
import os
import re
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
TARGET_MAC = sys.argv[2] if len(sys.argv) > 2 else None
OUTPUT = sys.argv[3] if len(sys.argv) > 3 else "rssi_log.csv"

HEADER = ["date", "time", "mac", "channel", "samples",
          "last_dbm", "avg_dbm", "weakest_dbm", "strongest_dbm", "filtered_dbm"]
MAC_RE = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")

new_file = not os.path.exists(OUTPUT) or os.path.getsize(OUTPUT) == 0
if not new_file:
    with open(OUTPUT, newline="") as f:
        if next(csv.reader(f), None) != HEADER:
            sys.exit(f"{OUTPUT} has different columns (older log). "
                     f"Pass a new file name, e.g.: {sys.argv[0]} {PORT} MAC new_log.csv")

ser = serial.Serial(PORT, 115200, timeout=1)
time.sleep(2)  # opening the port may reset the ESP32; wait for it to boot
# Drop boot messages / half lines received while the port was opening.
ser.reset_input_buffer()

def send_mac():
    if TARGET_MAC:
        ser.write(f"MAC {TARGET_MAC}\n".encode())

send_mac()
ser.readline()  # first line may still be partial

with open(OUTPUT, "a", newline="") as f:
    writer = csv.writer(f)
    if new_file:
        writer.writerow(HEADER)

    print(f"Logging {PORT} -> {OUTPUT} (Ctrl+C to stop)")
    warned_old = False
    warned_repl = False
    warned_silent = False
    last_rx = time.time()
    try:
        while True:
            line = ser.readline().decode("ascii", errors="ignore").strip()
            if line:
                last_rx = time.time()
            elif not warned_silent and time.time() - last_rx > 5:
                print("No data from the ESP32 for 5 s: it is probably running "
                      "another sketch. Upload sketch_aug29c.ino to it.")
                warned_silent = True
            if not line or not line.isprintable():
                continue
            fields = line.split(",")
            is_row = MAC_RE.match(fields[0]) is not None
            # Only data rows go to the CSV; status messages are just shown.
            if is_row and len(fields) == 8:
                now = time.localtime()
                row = [time.strftime("%Y-%m-%d", now),
                       time.strftime("%H:%M:%S", now)] + fields
                writer.writerow(row)
                f.flush()
                print(",".join(row))
            elif is_row and len(fields) == 7:
                if not warned_old:
                    print("Old firmware (no filtered_dbm column): upload "
                          "sketch_aug29c.ino to the ESP32 again. Nothing is "
                          "being recorded.")
                    warned_old = True
            elif line.startswith(">>>") or line.startswith("Traceback"):
                if not warned_repl:
                    print("The ESP32 is running MicroPython, not the RSSI sniffer: "
                          "upload sketch_aug29c.ino to it. Nothing is being recorded.")
                    warned_repl = True
            else:
                print(line)
                if line.startswith("Waiting for target MAC"):
                    send_mac()  # ESP32 restarted and forgot the MAC
    except KeyboardInterrupt:
        print(f"\nStopped. Saved to {OUTPUT}")
    finally:
        ser.close()
