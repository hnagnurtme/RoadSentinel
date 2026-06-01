/**
 * ESP32 Smart Device — Fingerprint & Alert Speaker
 *
 * Tính năng:
 *  - Kết nối WiFi & MQTT Broker
 *  - Đăng ký nhận alert từ topic `roadsentinel/alerts/#`: khi có alert (sleeping, using_phone, v.v.),
 *    kích hoạt Buzzer/Speaker để cảnh báo tài xế. Tắt cảnh báo khi nhận trạng thái `normal`.
 *  - Cảm biến vân tay (AS608):
 *    - Quét vân tay (Check vân tay): gửi POST request tới API `/api/v1/users/fingerprint`
 *      để xác thực tài xế và bắt đầu driving session.
 *    - Đăng ký vân tay mới (Enroll): Nhận lệnh enroll qua MQTT topic `roadsentinel/commands/enroll`
 *      chứa `user_id`, hướng dẫn người dùng nhấn vân tay 2 lần để đăng ký vào cảm biến,
 *      sau đó gọi API PATCH `/api/v1/users/{user_id}/fingerprint` để lưu thông tin liên kết.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <HTTPClient.h>
#include <Adafruit_Fingerprint.h>
#include <ArduinoJson.h>

// ─── Cấu hình Kết nối ──────────────────────────────────────────────────────────
static const char* WIFI_SSID = "37 Ngo Van So";
static const char* WIFI_PASS = "987654321";

static const char* MQTT_SERVER = "192.168.1.188";
static const uint16_t MQTT_PORT = 1883;
static const char* MQTT_USER = "";
static const char* MQTT_PASS = "";

static const char* API_BASE_URL = "http://192.168.1.188:8000/api/v1";

// ─── Topic MQTT ───────────────────────────────────────────────────────────────
static const char* TOPIC_ALERTS = "roadsentinel/alerts/#";
static const char* TOPIC_ENROLL_CMD = "roadsentinel/commands/enroll";
static const char* TOPIC_ENROLL_RESULT = "roadsentinel/commands/enroll/result";

// ─── Cấu hình Pin ESP32 ────────────────────────────────────────────────────────
#define BUZZER_PIN 25      // Còi báo/Loa cảnh báo
#define STATUS_LED 2       // Đèn LED trạng thái
#define ENROLL_BUTTON 12   // Nút nhấn thủ công để kích hoạt enroll (optional)

// ─── Khởi tạo ngoại vi ────────────────────────────────────────────────────────
#if defined(ESP32)
  // ESP32 sử dụng HardwareSerial 2 (Pin 16 RX, Pin 17 TX)
  HardwareSerial mySerial(2);
#else
  // Boards khác sử dụng SoftwareSerial
  #include <SoftwareSerial.h>
  SoftwareSerial mySerial(2, 3);
#endif

Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// ─── Biến trạng thái ──────────────────────────────────────────────────────────
bool is_alerting = false;
unsigned long alert_start_time = 0;
const unsigned long ALARM_TIMEOUT = 180000; // 3 phút tự động tắt còi

// Trạng thái Enroll
bool enroll_mode = false;
String enroll_user_id = "";
int enroll_id = -1;

// ─── Hàm tiện ích còi báo ──────────────────────────────────────────────────────
void setBuzzer(bool active) {
  is_alerting = active;
  if (active) {
    digitalWrite(BUZZER_PIN, HIGH);
    digitalWrite(STATUS_LED, HIGH);
    alert_start_time = millis();
    Serial.println("[DEVICE] 🔔 BUZZER ON - Cảnh báo nguy hiểm!");
  } else {
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(STATUS_LED, LOW);
    Serial.println("[DEVICE] 🔕 BUZZER OFF - Trạng thái bình thường.");
  }
}

// ─── WiFi & Connection helpers ─────────────────────────────────────────────────
void setupWiFi() {
  delay(10);
  Serial.print("\n[WiFi] Connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Connected successfully");
  Serial.print("[WiFi] IP Address: ");
  Serial.println(WiFi.localIP());
}

// ─── Quét Vân Tay (Check và Bắt đầu Driving Session) ──────────────────────────
void checkFingerprint() {
  uint8_t p = finger.getImage();
  if (p != FINGERPRINT_OK) return; // Không có vân tay chạm vào

  p = finger.image2Tz();
  if (p != FINGERPRINT_OK) {
    Serial.println("[FINGER] Lỗi chuyển đổi ảnh vân tay.");
    return;
  }

  p = finger.fingerFastSearch();
  if (p == FINGERPRINT_OK) {
    Serial.printf("[FINGER] Tìm thấy vân tay khớp! ID: %d, Độ tin cậy: %d\n", finger.fingerID, finger.confidence);
    
    // Gọi API Backend bắt đầu phiên lái xe
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      String url = String(API_BASE_URL) + "/users/fingerprint";
      http.begin(url);
      http.addHeader("Content-Type", "application/json");

      JsonDocument doc;
      doc["fingerprint_id"] = "FINGER_" + String(finger.fingerID);
      String requestBody;
      serializeJson(doc, requestBody);

      Serial.print("[API] Đang gửi yêu cầu bắt đầu session: ");
      Serial.println(requestBody);

      int httpResponseCode = http.POST(requestBody);
      if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.printf("[API] Kết quả (%d): %s\n", httpResponseCode, response.c_str());
        // Nháy LED báo thành công
        for(int i=0; i<3; i++) {
          digitalWrite(STATUS_LED, HIGH); delay(100);
          digitalWrite(STATUS_LED, LOW); delay(100);
        }
      } else {
        Serial.printf("[API] Lỗi gửi HTTP POST: %s\n", http.errorToString(httpResponseCode).c_str());
      }
      http.end();
    }
  } else if (p == FINGERPRINT_NOTFOUND) {
    Serial.println("[FINGER] Vân tay chưa được đăng ký!");
    // Nháy LED nhanh báo lỗi
    digitalWrite(STATUS_LED, HIGH); delay(500);
    digitalWrite(STATUS_LED, LOW);
  } else {
    Serial.println("[FINGER] Lỗi đọc vân tay.");
  }
}

// ─── Đăng ký Vân Tay mới (Enroll) ─────────────────────────────────────────────
uint8_t getFingerprintEnroll() {
  int p = -1;
  Serial.printf("[ENROLL] Đang chờ đặt vân tay hợp lệ để đăng ký vào ID #%d...\n", enroll_id);
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    switch (p) {
      case FINGERPRINT_OK:
        Serial.println("[ENROLL] Đã nhận ảnh vân tay.");
        break;
      case FINGERPRINT_NOFINGER:
        break;
      default:
        Serial.println("[ENROLL] Lỗi đọc ảnh vân tay.");
        return p;
    }
    // Thoát nếu nhấn còi cảnh báo hoặc thoát trạng thái
    if (!enroll_mode) return FINGERPRINT_TIMEOUT;
    delay(100);
  }

  // OK success
  p = finger.image2Tz(1);
  if (p != FINGERPRINT_OK) {
    Serial.println("[ENROLL] Lỗi chuyển đổi ảnh vân tay lần 1.");
    return p;
  }

  Serial.println("[ENROLL] Nhấc ngón tay ra khỏi cảm biến...");
  delay(2000);
  p = 0;
  while (p != FINGERPRINT_NOFINGER) {
    p = finger.getImage();
    delay(100);
  }

  p = -1;
  Serial.println("[ENROLL] Đặt lại cùng ngón tay đó lần thứ 2...");
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    switch (p) {
      case FINGERPRINT_OK:
        Serial.println("[ENROLL] Đã nhận ảnh lần 2.");
        break;
      case FINGERPRINT_NOFINGER:
        break;
      default:
        Serial.println("[ENROLL] Lỗi đọc ảnh.");
        return p;
    }
    if (!enroll_mode) return FINGERPRINT_TIMEOUT;
    delay(100);
  }

  p = finger.image2Tz(2);
  if (p != FINGERPRINT_OK) {
    Serial.println("[ENROLL] Lỗi chuyển đổi ảnh vân tay lần 2.");
    return p;
  }

  // Tạo model vân tay
  p = finger.createModel();
  if (p == FINGERPRINT_OK) {
    Serial.println("[ENROLL] Hai ảnh vân tay khớp nhau!");
  } else {
    Serial.println("[ENROLL] Vân tay không khớp.");
    return p;
  }

  // Lưu vân tay vào bộ nhớ flash
  p = finger.storeModel(enroll_id);
  if (p == FINGERPRINT_OK) {
    Serial.printf("[ENROLL] Đăng ký thành công! Lưu tại ID #%d\n", enroll_id);
    return FINGERPRINT_OK;
  } else {
    Serial.println("[ENROLL] Lỗi lưu trữ vào flash.");
    return p;
  }
}

void startEnrollmentProcess() {
  // Tìm ID trống tiếp theo trên cảm biến
  int next_id = 1;
  while (next_id <= 127) {
    if (finger.loadModel(next_id) != FINGERPRINT_OK) {
      break; // Trống
    }
    next_id++;
  }
  enroll_id = next_id;
  Serial.printf("[ENROLL] Bắt đầu đăng ký vân tay mới tại ID trống: %d\n", enroll_id);

  digitalWrite(STATUS_LED, HIGH); // Sáng liên tục trong lúc enroll

  uint8_t res = getFingerprintEnroll();
  
  digitalWrite(STATUS_LED, LOW);

  if (res == FINGERPRINT_OK) {
    // Gọi API Backend PATCH để gán vân tay cho tài xế
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      String url = String(API_BASE_URL) + "/users/" + enroll_user_id + "/fingerprint";
      http.begin(url);
      http.addHeader("Content-Type", "application/json");

      JsonDocument doc;
      doc["fingerprint_id"] = "FINGER_" + String(enroll_id);
      String requestBody;
      serializeJson(doc, requestBody);

      Serial.printf("[API] Gửi liên kết vân tay tới user %s: %s\n", enroll_user_id.c_str(), requestBody.c_str());

      int httpResponseCode = http.PATCH(requestBody);
      
      JsonDocument resDoc;
      resDoc["status"] = "success";
      resDoc["user_id"] = enroll_user_id;
      resDoc["fingerprint_id"] = "FINGER_" + String(enroll_id);
      resDoc["code"] = httpResponseCode;
      
      String responseBody;
      serializeJson(resDoc, responseBody);
      mqttClient.publish(TOPIC_ENROLL_RESULT, responseBody.c_str());
      
      if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.printf("[API] Kết quả liên kết: %s\n", response.c_str());
      } else {
        Serial.printf("[API] Lỗi HTTP PATCH: %s\n", http.errorToString(httpResponseCode).c_str());
      }
      http.end();
    }
  } else {
    Serial.println("[ENROLL] Đăng ký thất bại hoặc bị hủy bỏ.");
    JsonDocument resDoc;
    resDoc["status"] = "failed";
    resDoc["user_id"] = enroll_user_id;
    resDoc["reason"] = "sensor_error_or_timeout";
    
    String responseBody;
    serializeJson(resDoc, responseBody);
    mqttClient.publish(TOPIC_ENROLL_RESULT, responseBody.c_str());
  }

  // Kết thúc chế độ enroll
  enroll_mode = false;
  enroll_user_id = "";
}

// ─── MQTT Message Callback ───────────────────────────────────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String topicStr = String(topic);
  String payloadStr = "";
  for (unsigned int i = 0; i < length; i++) {
    payloadStr += (char)payload[i];
  }

  Serial.printf("[MQTT] Message arrived [%s]: %s\n", topic, payloadStr.c_str());

  // 1. Nhận tin nhắn cảnh báo (alerts)
  if (topicStr.startsWith("roadsentinel/alerts/")) {
    JsonDocument doc;
    deserializeJson(doc, payloadStr);
    String event = doc["event"] | "normal";

    if (event == "normal") {
      setBuzzer(false);
    } else if (event == "sleeping" || event == "using_phone" || event == "distracted" || event == "drowsy") {
      setBuzzer(true);
    }
  }
  // 2. Nhận tin nhắn bắt đầu đăng ký vân tay mới (enroll)
  else if (topicStr == TOPIC_ENROLL_CMD) {
    JsonDocument doc;
    deserializeJson(doc, payloadStr);
    String user_id = doc["user_id"] | "";
    if (user_id != "") {
      enroll_user_id = user_id;
      enroll_mode = true;
      // Việc xử lý enroll sẽ được luồng chính (loop) bắt và thực hiện để không block MQTT client
      Serial.printf("[MQTT] Yêu cầu Enroll vân tay cho User: %s\n", enroll_user_id.c_str());
    }
  }
}

// ─── Kết nối lại MQTT ──────────────────────────────────────────────────────────
void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Attempting connection...");
    // Tạo ID ngẫu nhiên cho client
    String clientId = "RoadSentinelDevice-" + String(random(0xffff), HEX);
    
    if (mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)) {
      Serial.println("connected ✓");
      // Subscribe lại các topic
      mqttClient.subscribe(TOPIC_ALERTS);
      mqttClient.subscribe(TOPIC_ENROLL_CMD);
      Serial.println("[MQTT] Subscribed to alert and enroll topics");
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

// ─── Setup ───────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println("\n=== RoadSentinel IoT Smart Device Setup ===");

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(STATUS_LED, OUTPUT);
  pinMode(ENROLL_BUTTON, INPUT_PULLUP);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(STATUS_LED, LOW);

  // Khởi động cảm biến vân tay
  Serial.println("[FINGER] Initializing sensor...");
  finger.begin(57600);
  delay(100);

  if (finger.verifyPassword()) {
    Serial.println("[FINGER] Found fingerprint sensor ✓");
  } else {
    Serial.println("[FINGER] Did not find fingerprint sensor! Please check your connections.");
  }

  // Kết nối WiFi
  setupWiFi();

  // Khởi động MQTT
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  
  // Tăng buffer size cho JSON payloads lớn
  mqttClient.setBufferSize(512);
}

// ─── Loop ────────────────────────────────────────────────────────────────────
void loop() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  // Kiểm tra còi báo tự tắt sau timeout 3 phút
  if (is_alerting && (millis() - alert_start_time > ALARM_TIMEOUT)) {
    setBuzzer(false);
    Serial.println("[DEVICE] Cảnh báo còi tự động tắt do quá thời gian 3 phút.");
  }

  // Xử lý Enroll nếu có yêu cầu
  if (enroll_mode) {
    startEnrollmentProcess();
  } else {
    // Quét vân tay liên tục khi ở trạng thái hoạt động bình thường
    checkFingerprint();
  }

  delay(50); // Tiết kiệm điện / tránh overload CPU
}