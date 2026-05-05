#include <Arduino.h>
#include <SoftwareSerial.h>
#include <DFRobotDFPlayerMini.h>

SoftwareSerial mySoftSerial(19, 18); // RX=GPIO19, TX=GPIO18
DFRobotDFPlayerMini myDFPlayer;

void setup() {
  Serial.begin(115200);
  mySoftSerial.begin(9600);

  Serial.println("Khởi động DFPlayer...");

  if (!myDFPlayer.begin(mySoftSerial)) {
    Serial.println("Không tìm thấy DFPlayer! Kiểm tra:");
    Serial.println("  - Dây nối đúng chưa?");
    Serial.println("  - Có thẻ SD không?");
    Serial.println("  - Điện trở 1kΩ trên TX chưa?");
    while (true); // dừng lại
  }

  Serial.println("DFPlayer sẵn sàng!");
  myDFPlayer.volume(20);  // âm lượng 0–30
  myDFPlayer.play(1);     // phát file 0001.mp3
}

void loop() {
  // In trạng thái nếu có thay đổi
  if (myDFPlayer.available()) {
    uint8_t type = myDFPlayer.readType();
    int value    = myDFPlayer.read();

    switch (type) {
      case DFPlayerPlayFinished:
        Serial.print("Phát xong bài: ");
        Serial.println(value);
        // Tự động phát bài tiếp theo
        myDFPlayer.next();
        break;
      case DFPlayerError:
        Serial.print("Lỗi: ");
        Serial.println(value);
        break;
      case DFPlayerCardInserted:
        Serial.println("Đã cắm thẻ SD");
        break;
      case DFPlayerCardRemoved:
        Serial.println("Thẻ SD bị rút");
        break;
    }
  }
}