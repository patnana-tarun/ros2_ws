/*
  ESP32 passive Raspberry Pi RSSI sniffer

  Target board:
    ESP32 DevKit V1 / ESP-WROOM-32

  Purpose:
    - Does NOT join the IBSS or BATMAN-adv mesh.
    - Passively listens on one 2.4 GHz Wi-Fi channel.
    - Lets the user enter a Raspberry Pi Wi-Fi MAC in Serial Monitor.
    - Reports RSSI only for frames transmitted by that MAC.

  Arduino IDE:
    Board: ESP32 Dev Module
    Serial Monitor: 115200 baud, Newline

  Commands:
    MAC d8:3a:dd:13:54:64
    d8:3a:dd:13:54:64
    CHANNEL 1
    STATUS
    CLEAR

  Important:
    Enter the physical Wi-Fi interface MAC (wlan0/wlp...), not the bat0 MAC.

  CSV logging:
    Every second one CSV row is printed:
      mac,channel,samples,last_dbm,avg_dbm,weakest_dbm,strongest_dbm,filtered_dbm
    filtered_dbm = median-of-3 + EMA of avg_dbm; use it for relay-drop decisions.
    Close the Serial Monitor and run on the PC:
      python3 rssi_csv_logger.py /dev/ttyUSB0 d8:3a:dd:13:54:64
    It saves the rows to rssi_log.csv with an HH:MM:SS time column.
*/

#include <Arduino.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <ctype.h>

static uint8_t wifiChannel = 1;
static uint8_t targetMac[6] = {0};
static bool targetIsSet = false;

static portMUX_TYPE statsMux = portMUX_INITIALIZER_UNLOCKED;
static uint32_t sampleCount = 0;
static int32_t rssiSum = 0;
static int8_t lastRssi = 0;
static int8_t weakestRssi = 0;
static int8_t strongestRssi = 0;

static unsigned long lastReportMs = 0;
static String serialLine;

// RSSI smoothing for the relay-drop threshold: median-of-3, then an
// exponential moving average. The median removes single-second fades
// (e.g. one -71 dBm second among -53s) so they cannot trigger a false
// relay drop; the EMA smooths the remaining jitter. Only touched from
// loop(), so no lock is needed.
static const float FILTER_ALPHA = 0.35f;  // higher = faster, noisier
static float medianWindow[3];
static uint8_t medianCount = 0;
static float filteredRssi = 0.0f;
static bool filterReady = false;

static void resetFilter() {
  medianCount = 0;
  filterReady = false;
}

static float median3(float a, float b, float c) {
  if (a > b) {
    const float t = a;
    a = b;
    b = t;
  }
  if (b > c) b = c;
  return (a > b) ? a : b;
}

static float updateFilter(float sample) {
  medianWindow[0] = medianWindow[1];
  medianWindow[1] = medianWindow[2];
  medianWindow[2] = sample;
  if (medianCount < 3) ++medianCount;

  const float median = (medianCount < 3)
      ? sample
      : median3(medianWindow[0], medianWindow[1], medianWindow[2]);

  if (!filterReady) {
    filteredRssi = median;
    filterReady = true;
  } else {
    filteredRssi += FILTER_ALPHA * (median - filteredRssi);
  }
  return filteredRssi;
}

static void resetStatsLocked() {
  sampleCount = 0;
  rssiSum = 0;
  lastRssi = 0;
  weakestRssi = 0;
  strongestRssi = 0;
}

static void resetStats() {
  portENTER_CRITICAL(&statsMux);
  resetStatsLocked();
  portEXIT_CRITICAL(&statsMux);
}

static bool macEquals(const uint8_t *a, const uint8_t *b) {
  for (int i = 0; i < 6; ++i) {
    if (a[i] != b[i]) {
      return false;
    }
  }
  return true;
}

static void printMac(const uint8_t *mac) {
  for (int i = 0; i < 6; ++i) {
    if (i > 0) {
      Serial.print(':');
    }
    if (mac[i] < 0x10) {
      Serial.print('0');
    }
    Serial.print(mac[i], HEX);
  }
}

static int hexValue(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

static bool parseMac(String text, uint8_t parsed[6]) {
  String hexOnly;
  text.trim();

  for (size_t i = 0; i < text.length(); ++i) {
    const char c = text.charAt(i);
    if (isxdigit(static_cast<unsigned char>(c))) {
      hexOnly += c;
    } else if (c == ':' || c == '-' || c == '.' || c == ' ') {
      // Accepted separators.
    } else {
      return false;
    }
  }

  if (hexOnly.length() != 12) {
    return false;
  }

  for (int i = 0; i < 6; ++i) {
    const int high = hexValue(hexOnly.charAt(i * 2));
    const int low = hexValue(hexOnly.charAt(i * 2 + 1));
    if (high < 0 || low < 0) {
      return false;
    }
    parsed[i] = static_cast<uint8_t>((high << 4) | low);
  }

  return true;
}

// For 802.11 management and data frames, Address 2 (bytes 10..15) is the
// transmitter address. In your IBSS network, this identifies the Pi radio
// that physically transmitted the captured frame.
static void snifferCallback(void *buffer, wifi_promiscuous_pkt_type_t packetType) {
  if (packetType != WIFI_PKT_MGMT && packetType != WIFI_PKT_DATA) {
    return;
  }

  const wifi_promiscuous_pkt_t *packet =
      reinterpret_cast<const wifi_promiscuous_pkt_t *>(buffer);

  if (packet->rx_ctrl.sig_len < 16) {
    return;
  }

  const uint8_t *frame = packet->payload;
  const uint16_t frameControl = frame[0] | (static_cast<uint16_t>(frame[1]) << 8);
  const uint8_t ieee80211Type = (frameControl >> 2) & 0x03;

  // Type 0 = management, type 2 = data. Ignore control/reserved frames.
  if (ieee80211Type != 0 && ieee80211Type != 2) {
    return;
  }

  const uint8_t *transmitterMac = frame + 10;
  uint8_t selectedMac[6];
  bool selected;

  portENTER_CRITICAL(&statsMux);
  selected = targetIsSet;
  for (int i = 0; i < 6; ++i) {
    selectedMac[i] = targetMac[i];
  }
  portEXIT_CRITICAL(&statsMux);

  if (!selected || !macEquals(transmitterMac, selectedMac)) {
    return;
  }

  const int8_t rssi = packet->rx_ctrl.rssi;

  portENTER_CRITICAL(&statsMux);
  if (sampleCount == 0) {
    weakestRssi = rssi;
    strongestRssi = rssi;
  } else {
    if (rssi < weakestRssi) weakestRssi = rssi;
    if (rssi > strongestRssi) strongestRssi = rssi;
  }
  lastRssi = rssi;
  rssiSum += rssi;
  ++sampleCount;
  portEXIT_CRITICAL(&statsMux);
}

static void showStatus() {
  Serial.print("Channel: ");
  Serial.print(wifiChannel);
  Serial.print(" | Target: ");

  portENTER_CRITICAL(&statsMux);
  const bool selected = targetIsSet;
  uint8_t selectedMac[6];
  for (int i = 0; i < 6; ++i) {
    selectedMac[i] = targetMac[i];
  }
  portEXIT_CRITICAL(&statsMux);

  if (selected) {
    printMac(selectedMac);
  } else {
    Serial.print("not set");
  }
  Serial.println();
}

static void setTargetMac(const uint8_t parsed[6]) {
  portENTER_CRITICAL(&statsMux);
  for (int i = 0; i < 6; ++i) {
    targetMac[i] = parsed[i];
  }
  targetIsSet = true;
  resetStatsLocked();
  portEXIT_CRITICAL(&statsMux);
  resetFilter();

  Serial.print("Target MAC set to: ");
  printMac(parsed);
  Serial.println();
}

static void setSnifferChannel(uint8_t newChannel) {
  if (newChannel < 1 || newChannel > 13) {
    Serial.println("ERROR: For this 2.4 GHz test, enter CHANNEL 1 to CHANNEL 13.");
    return;
  }

  esp_wifi_set_promiscuous(false);
  const esp_err_t result =
      esp_wifi_set_channel(newChannel, WIFI_SECOND_CHAN_NONE);

  if (result == ESP_OK) {
    wifiChannel = newChannel;
    resetStats();
    resetFilter();
    Serial.print("Sniffer channel set to: ");
    Serial.println(wifiChannel);
  } else {
    Serial.print("ERROR: esp_wifi_set_channel failed with code ");
    Serial.println(static_cast<int>(result));
  }

  esp_wifi_set_promiscuous(true);
}

static void processCommand(String command) {
  command.trim();
  if (command.length() == 0) {
    return;
  }

  String upper = command;
  upper.toUpperCase();

  if (upper == "STATUS") {
    showStatus();
    return;
  }

  if (upper == "CLEAR") {
    portENTER_CRITICAL(&statsMux);
    targetIsSet = false;
    for (int i = 0; i < 6; ++i) targetMac[i] = 0;
    resetStatsLocked();
    portEXIT_CRITICAL(&statsMux);
    resetFilter();
    Serial.println("Target MAC cleared.");
    return;
  }

  if (upper.startsWith("CHANNEL ")) {
    String value = command.substring(8);
    value.trim();
    setSnifferChannel(static_cast<uint8_t>(value.toInt()));
    return;
  }

  String macText = command;
  if (upper.startsWith("MAC ")) {
    macText = command.substring(4);
    macText.trim();
  }

  uint8_t parsed[6];
  if (parseMac(macText, parsed)) {
    setTargetMac(parsed);
  } else {
    Serial.println("ERROR: Enter MAC aa:bb:cc:dd:ee:ff, CHANNEL 1, STATUS, or CLEAR.");
  }
}

static void readSerialCommands() {
  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\n' || c == '\r') {
      if (serialLine.length() > 0) {
        processCommand(serialLine);
        serialLine = "";
      }
    } else if (serialLine.length() < 80) {
      serialLine += c;
    }
  }
}

static void reportRssi() {
  bool selected;
  uint8_t selectedMac[6];
  uint32_t count;
  int32_t sum;
  int8_t last;
  int8_t weakest;
  int8_t strongest;

  portENTER_CRITICAL(&statsMux);
  selected = targetIsSet;
  for (int i = 0; i < 6; ++i) selectedMac[i] = targetMac[i];
  count = sampleCount;
  sum = rssiSum;
  last = lastRssi;
  weakest = weakestRssi;
  strongest = strongestRssi;
  resetStatsLocked();
  portEXIT_CRITICAL(&statsMux);

  if (!selected) {
    Serial.println("Waiting for target MAC. Enter: MAC aa:bb:cc:dd:ee:ff");
    return;
  }

  // One CSV row per report:
  // mac,channel,samples,last_dbm,avg_dbm,weakest_dbm,strongest_dbm,filtered_dbm
  // The HH:MM:SS timestamp is added by rssi_csv_logger.py on the PC,
  // because the ESP32 has no real-time clock.
  printMac(selectedMac);
  Serial.print(',');
  Serial.print(wifiChannel);
  Serial.print(',');
  Serial.print(count);

  if (count == 0) {
    // No frames this second: leave the filter state untouched.
    Serial.println(",,,,,");
    return;
  }

  const float average = static_cast<float>(sum) / static_cast<float>(count);
  const float filtered = updateFilter(average);
  Serial.print(',');
  Serial.print(last);
  Serial.print(',');
  Serial.print(average, 1);
  Serial.print(',');
  Serial.print(weakest);
  Serial.print(',');
  Serial.print(strongest);
  Serial.print(',');
  Serial.println(filtered, 1);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  WiFi.setSleep(false);
  delay(100);

  wifi_promiscuous_filter_t filter;
  filter.filter_mask = WIFI_PROMIS_FILTER_MASK_MGMT |
                       WIFI_PROMIS_FILTER_MASK_DATA;

  esp_wifi_set_promiscuous(false);
  esp_wifi_set_promiscuous_filter(&filter);
  esp_wifi_set_promiscuous_rx_cb(&snifferCallback);

  const esp_err_t channelResult =
      esp_wifi_set_channel(wifiChannel, WIFI_SECOND_CHAN_NONE);
  const esp_err_t snifferResult = esp_wifi_set_promiscuous(true);

  Serial.println();
  Serial.println("ESP32 Raspberry Pi RSSI sniffer started.");
  Serial.println("Enter the Pi physical Wi-Fi MAC, for example:");
  Serial.println("MAC d8:3a:dd:13:54:64");
  Serial.println("Commands: MAC <address>, CHANNEL <1-13>, STATUS, CLEAR");
  Serial.print("Initial channel: ");
  Serial.println(wifiChannel);

  if (channelResult != ESP_OK || snifferResult != ESP_OK) {
    Serial.print("WARNING: Wi-Fi initialization returned channel=");
    Serial.print(static_cast<int>(channelResult));
    Serial.print(" sniffer=");
    Serial.println(static_cast<int>(snifferResult));
  }

  lastReportMs = millis();
}

void loop() {
  readSerialCommands();

  const unsigned long now = millis();
  if (now - lastReportMs >= 1000) {
    lastReportMs = now;
    reportRssi();
  }

  delay(5);
}
