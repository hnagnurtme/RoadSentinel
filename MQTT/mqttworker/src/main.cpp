#include <HardwareSerial.h>

HardwareSerial mySerial(2);

// 👉 chỉnh lại đúng chân bạn đang dùng
#define RX_PIN 4
#define TX_PIN 5

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n=== UART DEBUG START ===");

  // thử cả 2 baud phổ biến
  mySerial.begin(57600, SERIAL_8N1, RX_PIN, TX_PIN);

  Serial.println("UART started (57600)");
}

void loop() {
  // kiểm tra có data từ sensor không
  if (mySerial.available()) {
    Serial.print("DATA: ");

    while (mySerial.available()) {
      uint8_t c = mySerial.read();
      Serial.print("0x");
      if (c < 16) Serial.print("0");
      Serial.print(c, HEX);
      Serial.print(" ");
    }

    Serial.println();
  } else {
    static unsigned long last = 0;
    if (millis() - last > 2000) {
      Serial.println("No data from sensor...");
      last = millis();
    }
  }
}