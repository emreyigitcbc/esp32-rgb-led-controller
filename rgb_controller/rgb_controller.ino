#include <WiFi.h>
#include <PubSubClient.h>
#include <EEPROM.h>


#include <WiFi.h>
#include <PubSubClient.h>
#include <EEPROM.h>
#include <ArduinoJson.h>

// WiFi Credentials
const char* ssid = "ENTER_YOUR_WIFI_SSID";
const char* password = "ENTER_YOUR_WIFI_PASS";

// Public MQTT Broker Settings
const char* mqtt_server = "MQTT_SERVER";
const int mqtt_port = 1883;
const char* mqtt_topic = "TOPIC";

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Network non-blocking timing variables
unsigned long lastReconnectAttempt = 0;

// --- Hardware Pins ---
const int pinRed = 8;
const int pinGreen = 10;
const int pinBlue = 12;

// --- Data Structures ---
struct LedConfig {
  uint8_t initFlag;       
  uint8_t mode;           
  uint16_t speed;         
  uint8_t colorCount;     
  uint8_t colors[10][3];  
};

LedConfig currentConfig;

// --- State Machine Variables ---
unsigned long previousMillis = 0;
uint8_t currentStep = 0;
uint8_t colorIndex = 0;
int8_t breatheDir = 1;    
bool strobeState = false;

// --- Hardware Control ---
void setLEDColor(uint8_t red, uint8_t green, uint8_t blue) {
  analogWrite(pinRed, red);
  analogWrite(pinGreen, green);
  analogWrite(pinBlue, blue);
}

// --- Animation Handlers ---
void handleSolid() {
  setLEDColor(currentConfig.colors[0][0], currentConfig.colors[0][1], currentConfig.colors[0][2]);
}

void handleBreathe() {
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= currentConfig.speed) {
    previousMillis = currentMillis;
    
    float intensity = currentStep / 255.0;
    setLEDColor(
      currentConfig.colors[0][0] * intensity,
      currentConfig.colors[0][1] * intensity,
      currentConfig.colors[0][2] * intensity
    );

    currentStep += breatheDir;
    if (currentStep == 255 || currentStep == 0) {
      breatheDir = -breatheDir;
    }
  }
}

void handleCrossfade() {
  if (currentConfig.colorCount < 2) {
    handleSolid(); 
    return;
  }

  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= currentConfig.speed) {
    previousMillis = currentMillis;

    uint8_t nextIndex = (colorIndex + 1) % currentConfig.colorCount;

    int r = map(currentStep, 0, 255, currentConfig.colors[colorIndex][0], currentConfig.colors[nextIndex][0]);
    int g = map(currentStep, 0, 255, currentConfig.colors[colorIndex][1], currentConfig.colors[nextIndex][1]);
    int b = map(currentStep, 0, 255, currentConfig.colors[colorIndex][2], currentConfig.colors[nextIndex][2]);

    setLEDColor(r, g, b);

    currentStep++;
    if (currentStep == 0) {
      colorIndex = nextIndex; 
    }
  }
}

void handleStrobe() {
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= currentConfig.speed) {
    previousMillis = currentMillis;
    strobeState = !strobeState;

    if (strobeState) {
      setLEDColor(currentConfig.colors[colorIndex][0], currentConfig.colors[colorIndex][1], currentConfig.colors[colorIndex][2]);
    } else {
      setLEDColor(0, 0, 0);
      colorIndex = (colorIndex + 1) % currentConfig.colorCount;
    }
  }
}

// --- Configuration Management ---
void loadConfiguration() {
  EEPROM.begin(sizeof(LedConfig));
  EEPROM.get(0, currentConfig);

  if (currentConfig.initFlag != 0xAA) {
    Serial.println("Formatting EEPROM and setting defaults...");
    currentConfig.initFlag = 0xAA;
    currentConfig.mode = 0;        
    currentConfig.speed = 10;      
    currentConfig.colorCount = 1;  
    
    currentConfig.colors[0][0] = 128;
    currentConfig.colors[0][1] = 0;
    currentConfig.colors[0][2] = 128;

    EEPROM.put(0, currentConfig);
    EEPROM.commit();
  } else {
    Serial.println("Booting with saved EEPROM configuration.");
  }
}

void resetAnimationStates() {
  currentStep = 0;
  colorIndex = 0;
  breatheDir = 1;
  strobeState = false;
  setLEDColor(0, 0, 0); 
}

// --- Network and Communication ---
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.println("MQTT Packet Arrived.");

  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, payload, length);

  if (error) {
    Serial.print("JSON Error: ");
    Serial.println(error.c_str());
    return;
  }

  currentConfig.mode = doc["mode"] | currentConfig.mode;
  currentConfig.speed = doc["speed"] | currentConfig.speed;
  currentConfig.colorCount = doc["colorCount"] | currentConfig.colorCount;
  
  if (currentConfig.colorCount > 10) currentConfig.colorCount = 10;

  JsonArray newColors = doc["colors"].as<JsonArray>();
  int i = 0;
  for (JsonVariant v : newColors) {
    if (i >= 10) break;
    currentConfig.colors[i][0] = v[0] | 0;
    currentConfig.colors[i][1] = v[1] | 0;
    currentConfig.colors[i][2] = v[2] | 0;
    i++;
  }

  EEPROM.put(0, currentConfig);
  EEPROM.commit();
  Serial.println("New config saved.");

  resetAnimationStates();
}

void handleNetwork() {
  // If WiFi is disconnected, ESP32 auto-reconnects in the background
  // but we shouldn't attempt MQTT connection if WiFi is down
  if (WiFi.status() != WL_CONNECTED) {
    return; 
  }

  // Non-blocking MQTT reconnection handler
  if (!mqttClient.connected()) {
    unsigned long currentMillis = millis();
    // Try to connect every 5000 milliseconds
    if (currentMillis - lastReconnectAttempt > 5000) {
      lastReconnectAttempt = currentMillis;
      Serial.println("Attempting MQTT connection...");
      
      String clientId = "ESP32S3-RGB-" + String(random(0xffff), HEX);
      if (mqttClient.connect(clientId.c_str())) {
        Serial.println("MQTT Connected!");
        mqttClient.subscribe(mqtt_topic);
        lastReconnectAttempt = 0; // Reset timer on success
      } else {
        Serial.print("MQTT Failed, rc=");
        Serial.println(mqttClient.state());
      }
    }
  } else {
    // If connected, process incoming MQTT messages
    mqttClient.loop();
  }
}

// --- Main Program ---
void setup() {
  Serial.begin(115200);

  analogWriteResolution(pinRed, 8);
  analogWriteResolution(pinGreen, 8);
  analogWriteResolution(pinBlue, 8);
  analogWriteFrequency(pinRed, 5000);
  analogWriteFrequency(pinGreen, 5000);
  analogWriteFrequency(pinBlue, 5000);

  pinMode(pinRed, OUTPUT);
  pinMode(pinGreen, OUTPUT);
  pinMode(pinBlue, OUTPUT);

  // Load EEPROM and apply hardware states immediately
  loadConfiguration();
  
  // Initialize WiFi connection without blocking the boot process
  Serial.println("Starting WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(mqttCallback);
}

void loop() {
  // Manage WiFi/MQTT connection asynchronously
  handleNetwork();

  // Run the LED animation continuously, regardless of network status
  switch (currentConfig.mode) {
    case 0:
      handleSolid();
      break;
    case 1:
      handleBreathe();
      break;
    case 2:
      handleCrossfade();
      break;
    case 3:
      handleStrobe();
      break;
    default:
      handleSolid(); 
      break;
  }
}