#include <Arduino.h>

#define LED_BUILTIN_RED 33  // LED đỏ nhỏ phía sau board CAM
#define LED_FLASH 4         // LED trắng cực sáng phía trước

void setup() {
    Serial.begin(115200);
    pinMode(LED_BUILTIN_RED, OUTPUT);
    pinMode(LED_FLASH, OUTPUT);
    
    Serial.println("ESP32-CAM da khoi dong!");
}

void loop() {
    // Nháy LED đỏ phía sau (Logic ngược: LOW là sáng)
    digitalWrite(LED_BUILTIN_RED, LOW); 
    Serial.println("LED RED ON");
    delay(500);
    
    digitalWrite(LED_BUILTIN_RED, HIGH);
    Serial.println("LED RED OFF");
    delay(500);
}