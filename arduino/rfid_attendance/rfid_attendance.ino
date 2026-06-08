/*
 * RFID Attendance System — ESP8266 + RC522
 *
 * Wiring:
 *   RC522  → NodeMCU
 *   SDA    → D8  (SS_PIN)
 *   SCK    → D5
 *   MOSI   → D7
 *   MISO   → D6
 *   RST    → D3  (RST_PIN)
 *   3.3V   → 3V3
 *   GND    → GND
 *
 *   Green LED (+) → D1 → 220Ω → GND
 *   Red   LED (+) → D2 → 220Ω → GND
 *
 * Libraries needed (install via Arduino Library Manager):
 *   - MFRC522  by GithubCommunity
 *   - ArduinoJson  by Benoit Blanchon (v6.x)
 *   - ESP8266WiFi  (bundled with ESP8266 board package)
 *   - ESP8266HTTPClient (bundled)
 */

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>

// ── Configuration ──────────────────────────────────────────────────────────

const char* WIFI_SSID     = "<wifi-ssid>";
const char* WIFI_PASSWORD = "<wifi-password>";

const char* SERVER_URL = "<server-url>/mark-attendance";

// ── Pin Definitions ────────────────────────────────────────────────────────

#define SS_PIN    D8
#define RST_PIN   D3
#define GREEN_LED D1
#define RED_LED   D2

// ── Globals ────────────────────────────────────────────────────────────────

MFRC522 rfid(SS_PIN, RST_PIN);
WiFiClientSecure wifiClient;

// ── Setup ──────────────────────────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    SPI.begin();
    rfid.PCD_Init();

    pinMode(GREEN_LED, OUTPUT);
    pinMode(RED_LED, OUTPUT);
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, LOW);

    wifiClient.setInsecure();   // accept Railway's SSL cert without pinning
    connectWiFi();

    Serial.println("Ready — scan a card.");
    flashLED(GREEN_LED, 3, 150);
}

// ── Main loop ──────────────────────────────────────────────────────────────

void loop() {
    // Re-connect if WiFi dropped
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi lost — reconnecting…");
        connectWiFi();
    }

    if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
        delay(100);
        return;
    }

    String uid = readUID();
    Serial.println("Scanned UID: " + uid);

    sendAttendance(uid);

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    // Debounce — ignore re-scan for 1.5 s
    delay(1500);
}

// ── Helpers ────────────────────────────────────────────────────────────────

String readUID() {
    String uid = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
        if (rfid.uid.uidByte[i] < 0x10) uid += "0";
        uid += String(rfid.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();
    return uid;
}

void connectWiFi() {
    Serial.print("Connecting to ");
    Serial.print(WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries < 30) {
        digitalWrite(RED_LED, !digitalRead(RED_LED));
        delay(500);
        Serial.print(".");
        tries++;
    }
    digitalWrite(RED_LED, LOW);

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nConnected! IP: " + WiFi.localIP().toString());
    } else {
        Serial.println("\nFailed to connect. Check credentials.");
    }
}

void sendAttendance(const String& uid) {
    HTTPClient http;
    http.begin(wifiClient, SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(8000);

    // Build JSON payload
    StaticJsonDocument<64> req;
    req["rfid_uid"] = uid;
    String body;
    serializeJson(req, body);

    int code = http.POST(body);
    Serial.println("HTTP " + String(code));

    if (code == 200) {
        String resp = http.getString();
        StaticJsonDocument<256> doc;
        if (deserializeJson(doc, resp) == DeserializationError::Ok) {
            const char* studentName    = doc["student_name"];
            const char* attendanceType = doc["attendance_type"];
            Serial.printf("✓ %s — %s\n", studentName, attendanceType);
        }
        // Green: 2 flashes = IN, 1 flash = OUT
        String atype = doc["attendance_type"] | "IN";
        flashLED(GREEN_LED, atype == "IN" ? 2 : 1, 250);

    } else if (code == 404) {
        Serial.println("✗ Invalid RFID card");
        flashLED(RED_LED, 3, 200);

    } else if (code == 429) {
        Serial.println("✗ Duplicate scan — too fast");
        flashLED(RED_LED, 1, 600);

    } else {
        Serial.println("✗ Server error or no response");
        flashLED(RED_LED, 2, 300);
    }

    http.end();
}

void flashLED(int pin, int times, int delayMs) {
    for (int i = 0; i < times; i++) {
        digitalWrite(pin, HIGH);
        delay(delayMs);
        digitalWrite(pin, LOW);
        if (i < times - 1) delay(delayMs / 2);
    }
}
