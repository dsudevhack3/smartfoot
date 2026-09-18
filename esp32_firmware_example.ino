/*
 * SMARTFOOT ESP32 Hardware Firmware Sketch (Arduino IDE)
 * Connects ESP32 smart insole sensors to SmartFoot Flask Telemetry API
 * 
 * Hardware Required:
 * - ESP32 DevKit v1
 * - FSR Pressure Sensors (connected to ADC pins GPIO32, GPIO33, GPIO34, GPIO35, GPIO36, GPIO39)
 * - DS18B20 Temperature Sensors / Thermistors
 * - MPU6050 Accelerometer/Gyroscope IMU
 * 
 * Libraries Required (install via Arduino Library Manager):
 * - ArduinoJson (by Benoit Blanchon)
 * - HTTPClient (built-in for ESP32)
 * - WiFi (built-in for ESP32)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// -------------------------------------------------------------
// 1. WiFi & Server Configuration
// -------------------------------------------------------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Replace with your laptop/server IP address on the local network (e.g., http://192.168.1.100:5000)
const char* SERVER_URL    = "http://192.168.1.100:5000/api/v1/telemetry";

// Device Token assigned to this specific patient in SmartFoot database
// Pre-seeded Demo Tokens:
// Sita Devi   -> "dev-token-sita-101"
// Rajesh Kumar -> "dev-token-rajesh-102"
// Anita Sharma -> "dev-token-anita-103"
const char* DEVICE_TOKEN  = "dev-token-sita-101";

// -------------------------------------------------------------
// 2. Hardware Pin Mappings
// -------------------------------------------------------------
const int PIN_FSR_R_HEEL    = 32;
const int PIN_FSR_R_LAT_MID = 33;
const int PIN_FSR_R_MED_MID = 34;
const int PIN_FSR_R_MET1    = 35;
const int PIN_FSR_R_MET5    = 36;
const int PIN_FSR_R_HALLUX  = 39;

// Helper: Convert raw ADC analog reading (0-4095) to estimated pressure (kPa)
float adcToKpa(int adcValue) {
  // Linear/log scale approximation for standard FSR 402 sensors
  if (adcValue < 100) return 0.0;
  float voltage = (adcValue / 4095.0) * 3.3;
  float kPa = (voltage / 3.3) * 100.0; // 0 to 100 kPa estimation
  return kPa;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n=============================================");
  Serial.println("SMARTFOOT ESP32 Insole Telemetry Firmware");
  Serial.println("=============================================");

  // Initialize WiFi Connection
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected!");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    // ---------------------------------------------------------
    // 1. Read Analog Sensor Data (FSR Pressure Array)
    // ---------------------------------------------------------
    int raw_r_heel    = analogRead(PIN_FSR_R_HEEL);
    int raw_r_lat_mid = analogRead(PIN_FSR_R_LAT_MID);
    int raw_r_med_mid = analogRead(PIN_FSR_R_MED_MID);
    int raw_r_met1    = analogRead(PIN_FSR_R_MET1);
    int raw_r_met5    = analogRead(PIN_FSR_R_MET5);
    int raw_r_hallux  = analogRead(PIN_FSR_R_HALLUX);

    float kpa_r_heel    = adcToKpa(raw_r_heel);
    float kpa_r_lat_mid = adcToKpa(raw_r_lat_mid);
    float kpa_r_med_mid = adcToKpa(raw_r_med_mid);
    float kpa_r_met1    = adcToKpa(raw_r_met1);
    float kpa_r_met5    = adcToKpa(raw_r_met5);
    float kpa_r_hallux  = adcToKpa(raw_r_hallux);

    // Read DS18B20 / Thermal sensors (°C)
    float temp_left  = 31.8; // Set or read from DS18B20 Left probe
    float temp_right = 34.2; // Set or read from DS18B20 Right probe

    // ---------------------------------------------------------
    // 2. Build JSON Payload
    // ---------------------------------------------------------
    StaticJsonDocument<512> doc;
    doc["device_token"] = DEVICE_TOKEN;
    doc["is_simulated"] = false; // Flag as REAL ESP32 hardware telemetry

    JsonObject p_zones = doc.createNestedObject("pressure_zones");
    p_zones["R_heel"]    = kpa_r_heel;
    p_zones["R_lat_mid"] = kpa_r_lat_mid;
    p_zones["R_med_mid"] = kpa_r_med_mid;
    p_zones["R_met1"]    = kpa_r_met1;
    p_zones["R_met5"]    = kpa_r_met5;
    p_zones["R_hallux"]  = kpa_r_hallux;

    doc["temperature_left"]  = temp_left;
    doc["temperature_right"] = temp_right;

    JsonObject gait = doc.createNestedObject("gait_data");
    gait["cadence"]   = 104;
    gait["asymmetry"] = 14.5;
    gait["impact_g"]  = 1.3;

    String jsonPayload;
    serializeJson(doc, jsonPayload);

    // ---------------------------------------------------------
    // 3. Send HTTP POST to SmartFoot Backend API
    // ---------------------------------------------------------
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Token", DEVICE_TOKEN);

    Serial.print("Posting telemetry JSON to ");
    Serial.println(SERVER_URL);

    int httpResponseCode = http.POST(jsonPayload);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.print("HTTP Status Code: ");
      Serial.println(httpResponseCode);
      Serial.print("Server Response: ");
      Serial.println(response);
    } else {
      Serial.print("Error sending HTTP POST: ");
      Serial.println(httpResponseCode);
    }

    http.end(); // Free resources
  } else {
    Serial.println("WiFi Disconnected. Reconnecting...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  }

  // Send telemetry every 3 seconds
  delay(3000);
}
