// DRIVE PHASE — sprint timing gate node (ESP32 + IR break-beam sensor)
//
// The exact same sketch runs on all four gates. Only GATE_ID changes per board:
//   GATE_ID 0  ->  start gate (0m).  Breaks the beam, broadcasts "START", done.
//   GATE_ID 1  ->  10m gate.  Waits for "START", times its own beam break, reports the split.
//   GATE_ID 2  ->  30m gate.  Same as above.
//   GATE_ID 3  ->  60m / finish gate.  Same as above; its reported time is the total.
//
// Splits are computed on the receiver (software/receiver.py) from these raw
// cumulative elapsed times, so each gate only ever needs to know its own
// local clock — no time sync between boards required.
//
// ── Wiring ──
// IR break-beam sensor OUT pin -> BEAM_PIN (default GPIO 4)
// Sensor VCC -> 3V3 or 5V per your module's spec, GND -> GND
// Most cheap IR obstacle/break-beam modules pull OUT low when the beam is
// broken (open-collector with an onboard pull-up). If your beam reads
// "broken" when nothing is blocking it, flip BEAM_BROKEN_STATE below.

#include <WiFi.h>
#include <WiFiUdp.h>

// ── Per-board config — edit these four for every board you flash ──
const int GATE_ID = 1;                          // 0, 1, 2, or 3 — see header above
const char* WIFI_SSID     = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const IPAddress RECEIVER_IP(192, 168, 1, 50);    // static/reserved IP of the laptop running receiver.py

// ── Shared config — same on every board ──
const IPAddress BROADCAST_IP(192, 168, 1, 255);  // subnet broadcast address (match your WiFi's /24)
const uint16_t GATE_PORT = 8503;                  // must match UDP_PORT in receiver.py
const int BEAM_PIN = 4;
const int BEAM_BROKEN_STATE = LOW;                // flip to HIGH if your sensor is active-high
const unsigned long RETRIGGER_LOCKOUT_MS = 1500;  // ignore repeat breaks for this long after a trigger
const unsigned long ARM_TIMEOUT_MS = 15000;       // give up waiting for START after this long (gates 1-3)

WiFiUDP udp;
bool armed = false;              // gates 1-3: true once a START has been seen, waiting for our own break
unsigned long tStartMicros = 0;  // gates 1-3: micros() when START arrived
unsigned long armedAtMs = 0;
unsigned long lastTriggerMs = 0;

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected, IP: ");
  Serial.println(WiFi.localIP());
}

bool beamBroken() {
  return digitalRead(BEAM_PIN) == BEAM_BROKEN_STATE;
}

void sendUdp(IPAddress dest, const String& msg) {
  udp.beginPacket(dest, GATE_PORT);
  udp.write((const uint8_t*)msg.c_str(), msg.length());
  udp.endPacket();
}

void setup() {
  Serial.begin(115200);
  pinMode(BEAM_PIN, INPUT_PULLUP);
  connectWifi();
  udp.begin(GATE_PORT);  // gates 1-3 need this open to receive the START broadcast
  Serial.printf("Gate %d ready\n", GATE_ID);
}

void loopStartGate() {
  if (beamBroken() && millis() - lastTriggerMs > RETRIGGER_LOCKOUT_MS) {
    lastTriggerMs = millis();
    sendUdp(BROADCAST_IP, "START");
    Serial.println("Beam broken -> sent START");
  }
}

void loopSplitGate() {
  // Listen for the START broadcast from gate 0.
  int packetSize = udp.parsePacket();
  if (packetSize > 0 && !armed) {
    char buf[32];
    int len = udp.read(buf, sizeof(buf) - 1);
    buf[len] = '\0';
    if (String(buf) == "START") {
      armed = true;
      armedAtMs = millis();
      tStartMicros = micros();
      Serial.println("Armed — waiting for beam break");
    }
  }

  if (armed && millis() - armedAtMs > ARM_TIMEOUT_MS) {
    armed = false;  // no break within the window, reset and wait for the next run
    Serial.println("Timed out waiting for beam break — disarmed");
  }

  if (armed && beamBroken()) {
    float elapsedSec = (micros() - tStartMicros) / 1000000.0;
    String msg = "SPLIT:" + String(GATE_ID) + ":" + String(elapsedSec, 3);
    sendUdp(RECEIVER_IP, msg);
    Serial.println("Beam broken -> " + msg);
    armed = false;
    lastTriggerMs = millis();
    delay(RETRIGGER_LOCKOUT_MS);  // simple debounce before this gate can arm again
  }
}

void loop() {
  if (GATE_ID == 0) {
    loopStartGate();
  } else {
    loopSplitGate();
  }
}
