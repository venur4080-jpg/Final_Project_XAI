#include "MAX30105.h"
#include "heartRate.h"
#include <DallasTemperature.h>
#include <LiquidCrystal_I2C.h>
#include <OneWire.h>
#include <Wire.h>

/* ================== SENSOR OBJECTS ================== */
MAX30105 particleSensor;
LiquidCrystal_I2C
    lcd(0x27, 16,
        2); // Set the LCD address to 0x27 for a 16 chars and 2 line display

/* ================== PIN DEFINITIONS ================== */
// MAX30102 uses I2C (SDA, SCL) - Default on ESP32 is usually SDA=21, SCL=22
#define SOUND_PIN 35 // Sound sensor (ADC1)
#define TEMP_PIN 4   // DS18B20

/* ================== TEMPERATURE ================== */
OneWire oneWire(TEMP_PIN);
DallasTemperature sensors(&oneWire);

// Simulation Fallback
float calculateTemp(float currentBpm) {
  float estimated = 36.5 + ((currentBpm - 70.0) / 10.0);
  if (estimated < 36.0)
    estimated = 36.0;
  if (estimated > 42.0)
    estimated = 42.0;
  return estimated;
}

/* ================== VARIABLES ================== */
const byte RATE_SIZE = 6; // Average over 6 beats for stability
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;

float beatsPerMinute = 0;
int beatAvg = 0;
float currentTemp = 0;
int coughCount = 0;

/* ================== THRESHOLDS ================== */
int coughThreshold = 300; // Sound spike above baseline

/* ================== TIMING ================== */
unsigned long lastCoughTime = 0;
unsigned long lastTempTime = 0;

/* ================== STATE ================== */
int soundBaseline = 0;

/* ================== SETUP ================== */
void setup() {
  Serial.begin(115200);
  Serial.println("System Online");

  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("System Init...");
  delay(1000);
  lcd.clear();

  // Initialize Temperature Sensor
  sensors.begin();

  // Initialize MAX30102 (I2C)
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30102 was not found. Please check wiring/power.");
    // We don't hang (while(1)) so that Temp/Cough can still potentially work or
    // debug
  } else {
    // --- CUSTOM CONFIGURATION ---
    byte ledBrightness = 0x1F; // Lower brightness to prevent saturation
    byte sampleAverage = 4;
    byte ledMode = 2; // Red + IR
    int sampleRate = 400;
    int pulseWidth = 411;
    int adcRange = 4096;

    particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate,
                         pulseWidth, adcRange);
  }

  // Determine initial sound baseline
  soundBaseline = analogRead(SOUND_PIN);
}

/* ================== LOOP ================== */
void loop() {
  unsigned long now = millis();

  // 1. MAX30102 LOGIC
  long irValue = particleSensor.getIR();

  if (irValue > 50000 &&
      irValue < 250000) { // Finger detected and not saturated
    if (checkForBeat(irValue) == true) {
      long delta = now - lastBeat;
      lastBeat = now;

      beatsPerMinute = 60 / (delta / 1000.0);

      if (beatsPerMinute < 255 && beatsPerMinute > 20) {
        rates[rateSpot++] = (byte)beatsPerMinute;
        rateSpot %= RATE_SIZE;

        beatAvg = 0;
        for (byte x = 0; x < RATE_SIZE; x++)
          beatAvg += rates[x];
        beatAvg /= RATE_SIZE;
      }
    }
  } else {
    // No finger or saturated
    beatAvg = 0;
    beatsPerMinute = 0;
    // Reset average buffer to avoid stale values when finger returns
    for (byte x = 0; x < RATE_SIZE; x++)
      rates[x] = 0;
  }

  // 2. COUGH DETECTION (Sound Sensor)
  int soundRaw = analogRead(SOUND_PIN);
  soundBaseline = (soundBaseline * 9 + soundRaw) / 10; // Update moving average

  if ((soundRaw - soundBaseline) > coughThreshold) {
    if (now - lastCoughTime > 1000) {
      coughCount++;
      lastCoughTime = now;
    }
  }

  // 3. TEMPERATURE & SERIAL OUTPUT (Every 2 seconds)
  if (now - lastTempTime >= 2000) {
    sensors.requestTemperatures();
    float t = sensors.getTempCByIndex(0);

    if (t > -50 && t != DEVICE_DISCONNECTED_C) {
      currentTemp = t;
    } else {
      currentTemp = calculateTemp(beatAvg);
    }

    // FORMAT: "TEMP:xx.xC | BPM:xx | COUGHS:x"
    Serial.print("TEMP:");
    Serial.print(currentTemp, 1);
    Serial.print("C | BPM:");
    Serial.print(beatAvg);
    Serial.print(" | COUGHS:");
    Serial.println(coughCount);

    // Update LCD
    lcd.setCursor(0, 0); // Column 0, Line 0
    lcd.print("T:");
    lcd.print(currentTemp, 1);
    lcd.print("C B:");
    lcd.print(beatAvg);

    lcd.setCursor(0, 1); // Column 0, Line 1
    lcd.print("Coughs: ");
    lcd.print(coughCount);

    lastTempTime = now;
  }
}
