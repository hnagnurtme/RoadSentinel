#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Adafruit_Fingerprint.h>
#include "DFRobotDFPlayerMini.h"
#include <WiFi.h>
#include <esp_now.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include "mbedtls/md.h"
#include <time.h>

// Struct truyền dữ liệu tài xế qua ESP-NOW
struct DriverInfoMsg {
  char driver_id[37];
  char driver_name[33];
  char status[12];
};

// ==========================================================
// CẤU HÌNH WIFI VÀ THỜI GIAN
// ==========================================================
#define WIFI_SSID "37 Ngo Van So"
#define WIFI_PASSWORD "987654321"
#define NTP_SERVER "pool.ntp.org"
#define GMT_OFFSET_SEC 7 * 3600 // Việt Nam (GMT+7)
#define DAYLIGHT_OFFSET_SEC 0

// ==========================================================
// CẤU HÌNH API BACKEND & HMAC SECURITY
// ==========================================================
String api_base_url = "https://road-sentinel.trunganh.tech/api/v1";
#define HMAC_SECRET "roadsentinel_hmac_secret_key"

// ==========================================================
// CẤU HÌNH MQTT BROKER (HIVEMQ CLOUD SSL)
// ==========================================================
#define MQTT_SERVER "c0a6ae17c8da49c4b9ba9e3e4536a716.s1.eu.hivemq.cloud"
#define MQTT_PORT 8883
#define MQTT_USER "roadsentinel"
#define MQTT_PASS "Roadsentinel123"
#define MQTT_TOPIC_ALERTS "roadsentinel/alerts/#"
#define MQTT_TOPIC_ENROLL "roadsentinel/commands/enroll"
#define MQTT_TOPIC_ENROLL_RESULT "roadsentinel/commands/enroll/result"

// ==========================================================
// 1. CẤU HÌNH CHÂN VÂN TAY (Đã fix chạy thực tế)
// ==========================================================
#define FINGER_RX 17 // Dây Vàng (TX) của Vân tay cắm vào G17
#define FINGER_TX 16 // Dây Đen (RX) của Vân tay cắm vào G16
HardwareSerial fingerSerial(2);
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&fingerSerial);

// ==========================================================
// 2. CẤU HÌNH CHÂN MP3 (Đã fix chạy thực tế)
// ==========================================================
#define MP3_RX 27 // Chân số 3 (TX) của MP3 cắm vào G27
#define MP3_TX 26 // Chân số 2 (RX) của MP3 cắm vào G26
HardwareSerial mp3Serial(1);
DFRobotDFPlayerMini myDFPlayer;

// ==========================================================
// 3. CẤU HÌNH MÀN HÌNH LCD I2C (Mặc định G21, G22)
// ==========================================================
#define LCD_ADDR 0x27
LiquidCrystal_I2C lcd(LCD_ADDR, 16, 2);

// Khai báo hàm
String removeAccents(String str);
void lcdPrint(int col, int row, String text);
void hienThiManHinhCho();
void checkFingerprintAndDisplay();
void handleEnrollment();
void callback(char* topic, byte* payload, unsigned int length);
void reconnectMQTT();
void connectWiFi();
void syncTime();
String calculateHMAC(String message, String key);
void sendFingerprintCheck(int fingerID);
bool sendFingerprintEnroll(String user_id, int fingerID);
void sendEnrollResult(String user_id, String fingerprint_id, String error_msg);
uint8_t getFirstEmptyID();
uint8_t getFingerprintEnroll(int id);

// Trạng thái Enroll vân tay
bool isEnrolling = false;
String targetEnrollUserId = "";

WiFiClientSecure espClient;
PubSubClient client(espClient);

// ─── Cloud Connection Settings ───────────────────────────────────────────────
// Dynamic discovery removed - directly using cloud configuration.

// ==========================================================
// HÀM LOẠI BỎ DẤU TIẾNG VIỆT VÀ KÝ TỰ ĐẶC BIỆT (EMOJI) CHO LCD
// ==========================================================
String removeAccents(String str) {
  // Loại bỏ các emoji phổ biến để tránh lỗi font LCD
  str.replace("🎉", "");
  str.replace("🚨", "");
  str.replace("⚠️", "");
  
  // Mảng chứa các ký tự có dấu UTF-8 tiếng Việt
  const char* utf8_chars[] = {
    "á", "à", "ả", "ã", "ạ", "ă", "ắ", "ằ", "ẳ", "ẵ", "ặ", "â", "ấ", "ầ", "ẩ", "ẫ", "ậ",
    "Á", "À", "Ả", "Ã", "Ạ", "Ă", "Ắ", "Ằ", "Ẳ", "Ẵ", "Ặ", "Â", "Ấ", "Ầ", "Ẩ", "Ẫ", "Ậ",
    "é", "è", "ẻ", "ẽ", "ẹ", "ê", "ế", "ề", "ể", "ễ", "ệ",
    "É", "È", "Ẻ", "Ẽ", "Ẹ", "Ê", "Ế", "Ề", "Ể", "Ễ", "Ệ",
    "í", "ì", "ỉ", "ĩ", "ị",
    "Í", "Ì", "Ỉ", "Ĩ", "Ị",
    "ó", "ò", "ỏ", "õ", "ọ", "ô", "ố", "ồ", "ổ", "ỗ", "ộ", "ơ", "ớ", "ờ", "ở", "ỡ", "ợ",
    "Ó", "Ò", "Ỏ", "Õ", "Ọ", "Ô", "Ố", "Ồ", "Ổ", "Ỗ", "Ộ", "Ơ", "Ớ", "Ờ", "Ở", "Ỡ", "Ợ",
    "ú", "ù", "ủ", "ũ", "ụ", "ư", "ứ", "ừ", "ử", "ữ", "ự",
    "Ú", "Ù", "Ủ", "Ũ", "Ụ", "Ư", "Ứ", "Ừ", "Ử", "Ữ", "Ự",
    "ý", "ỳ", "ỷ", "ỹ", "ỵ",
    "Ý", "Ỳ", "Ý", "Ỹ", "Ỵ",
    "đ", "Đ"
  };
  
  // Mảng chứa các ký tự không dấu tương ứng
  const char* ascii_chars[] = {
    "a", "a", "a", "a", "a", "a", "a", "a", "a", "a", "a", "a", "a", "a", "a", "a", "a",
    "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A",
    "e", "e", "e", "e", "e", "e", "e", "e", "e", "e", "e",
    "E", "E", "E", "E", "E", "E", "E", "E", "E", "E", "E",
    "i", "i", "i", "i", "i",
    "I", "I", "I", "I", "I",
    "o", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o",
    "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O",
    "u", "u", "u", "u", "u", "u", "u", "u", "u", "u", "u",
    "U", "U", "U", "U", "U", "U", "U", "U", "U", "U", "U",
    "y", "y", "y", "y", "y",
    "Y", "Y", "Y", "Y", "Y",
    "d", "D"
  };
  
  int num_rules = sizeof(utf8_chars) / sizeof(utf8_chars[0]);
  for (int i = 0; i < num_rules; i++) {
    str.replace(utf8_chars[i], ascii_chars[i]);
  }
  return str;
}

// ==========================================================
// HÀM HIỂN THỊ CHỮ KHÔNG DẤU TẠI VỊ TRÍ CHỈ ĐỊNH TRÊN LCD
// ==========================================================
void lcdPrint(int col, int row, String text) {
  lcd.setCursor(col, row);
  lcd.print(removeAccents(text));
}

void setup()
{
  Serial.begin(9600);
  while (!Serial)
    ;
  delay(200);

  Serial.println("\n===========================================");
  Serial.println("🚀 KHỞI ĐỘNG HỆ THỐNG SMART DEVICE ROAD SENTINEL");
  Serial.println("===========================================");

  // --------------------------------------------------------
  // BƯỚC 1: KHỞI ĐỘNG VÀ KIỂM TRA MÀN HÌNH LCD I2C
  // --------------------------------------------------------
  // Khởi tạo I2C trên chân G21 (SDA) và G22 (SCL) trước khi kiểm tra
  Wire.begin(21, 22);
  delay(100); // Chờ bus I2C ổn định
  
  // Kiểm tra phản hồi từ địa chỉ LCD I2C với vòng lặp thử lại
  byte error = 1;
  for (int i = 0; i < 3; i++) {
    Wire.beginTransmission(LCD_ADDR);
    error = Wire.endTransmission();
    if (error == 0) break;
    delay(50);
  }
  
  // Khởi tạo màn hình
  lcd.init();
  lcd.backlight();
  lcd.clear();
  
  if (error == 0) {
    Serial.println("✅ Màn hình LCD I2C kết nối thành công!");
    lcd.setCursor(0, 0);
    lcd.print("  ROAD SENTINEL ");
    lcd.setCursor(0, 1);
    lcd.print("Screen Connected");
    delay(1000);
  } else {
    Serial.print("❌ LỖI PHẦN CỨNG: KHÔNG TÌM THẤY MÀN HÌNH LCD! Mã lỗi: ");
    Serial.println(error);
    Serial.println("Hãy kiểm tra lại dây SDA (G21), SCL (G22), GND và VCC.");
    lcd.setCursor(0, 0);
    lcd.print("SCREEN ERROR!");
    delay(1000);
  }

  // --------------------------------------------------------
  // BƯỚC 2: KHỞI ĐỘNG MODULE MP3 LOA
  // --------------------------------------------------------
  mp3Serial.begin(9600, SERIAL_8N1, MP3_RX, MP3_TX);
  Serial.print("Dang ket noi Module MP3... ");
  delay(2000); // Chờ 2 giây ổn định thẻ nhớ

  if (!myDFPlayer.begin(mp3Serial))
  {
    Serial.println("❌ LỖI!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("LOI PHAN CUNG:");
    lcd.setCursor(0, 1);
    lcd.print("KHONG TIM THAY MP3");
    while (true)
    {
      delay(1);
    } // Treo mạch bảo vệ nếu lỗi loa
  }
  Serial.println("✅ OK!");
  myDFPlayer.volume(27); // Thiết lập âm lượng ở mức an toàn (0 - 30) tránh sụt áp gây tắt loa
  delay(500);

  // --------------------------------------------------------
  // BƯỚC 3: KHỞI ĐỘNG CẢM BIẾN VÂN TAY
  // --------------------------------------------------------
  fingerSerial.begin(57600, SERIAL_8N1, FINGER_RX, FINGER_TX);
  Serial.print("Dang ket noi Cam bien Van tay... ");

  if (!finger.verifyPassword())
  {
    Serial.println("❌ LỖI!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("LOI PHAN CUNG:");
    lcd.setCursor(0, 1);
    lcd.print("LOI KET NOI VAN TAY");
    while (true)
    {
      delay(1);
    } // Treo mạch nếu lỏng dây vân tay
  }
  Serial.println("✅ OK!");

  // --------------------------------------------------------
  // BƯỚC 4: KẾT NỐI WIFI VÀ ĐỒNG BỘ THỜI GIAN
  // --------------------------------------------------------
  connectWiFi();
  
  Serial.println("[Connection] Using production cloud server.");
  
  syncTime();

  // --------------------------------------------------------
  // BƯỚC 4.5: KHỞI TẠO ESP-NOW
  // --------------------------------------------------------
  if (esp_now_init() == ESP_OK) {
    Serial.println("ESP-NOW Initialized successfully");
    esp_now_peer_info_t peerInfo = {};
    memset(&peerInfo, 0, sizeof(peerInfo));
    memset(peerInfo.peer_addr, 0xFF, 6); // Địa chỉ Broadcast
    peerInfo.channel = 0;
    peerInfo.encrypt = false;
    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
      Serial.println("Failed to add broadcast peer");
    }
  } else {
    Serial.println("Error initializing ESP-NOW");
  }

  // --------------------------------------------------------
  // BƯỚC 5: CẤU HÌNH MQTT
  // --------------------------------------------------------
  espClient.setInsecure(); // Bỏ qua việc xác thực chứng chỉ SSL của HiveMQ Cloud
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setCallback(callback);
  client.setBufferSize(512); // Tăng kích thước buffer để nhận gói tin JSON lớn (> 128 bytes)

  // --------------------------------------------------------
  // BƯỚC 6: HOÀN THÀNH KHỞI ĐỘNG -> VÀO TRẠNG THÁI SẴN SÀNG
  // --------------------------------------------------------
  Serial.println("\n👉 [HỆ THỐNG ĐÃ LÊN HẾT] HOÀN TOÀN SẴN SÀNG ĐỂ HOẠT ĐỘNG!");
  hienThiManHinhCho();
}

void loop()
{
  // Đảm bảo kết nối và xử lý MQTT nếu WiFi được kết nối
  if (WiFi.status() == WL_CONNECTED) {
    if (!client.connected()) {
      reconnectMQTT();
    }
    client.loop();
  }

  // Tùy theo trạng thái để xử lý quét vân tay điểm danh hoặc đăng ký mới
  if (isEnrolling) {
    handleEnrollment();
  } else {
    checkFingerprintAndDisplay();
  }
  
  delay(50); // Tránh quá tải CPU ESP32
}

// ==========================================================
// HÀM KẾT NỐI WIFI
// ==========================================================
void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiFi Connecting");
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempt = 0;
  while (WiFi.status() != WL_CONNECTED && attempt < 20) {
    delay(500);
    Serial.print(".");
    attempt++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Connected!");
    delay(1000);
  } else {
    Serial.println("\nWiFi connection failed! Proceeding offline...");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Failed!");
    delay(1500);
  }
}

// ==========================================================
// HÀM ĐỒNG BỘ THỜI GIAN QUA NTP
// ==========================================================
void syncTime() {
  if (WiFi.status() != WL_CONNECTED) return;
  
  Serial.println("Syncing time via NTP...");
  configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER, "time.nist.gov");
  
  time_t now = time(nullptr);
  int attempt = 0;
  while (now < 24 * 3600 && attempt < 10) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
    attempt++;
  }
  
  struct tm timeinfo;
  if (getLocalTime(&timeinfo)) {
    Serial.println("\nTime synced successfully!");
    Serial.println(&timeinfo, "%A, %B %d %Y %H:%M:%S");
  } else {
    Serial.println("\nFailed to sync time via NTP");
  }
}

// ==========================================================
// HÀM TÍNH TOÁN CHỮ KÝ HMAC-SHA256 (Dùng mbedtls của ESP32)
// ==========================================================
String calculateHMAC(String message, String key) {
  byte hmacResult[32];
  mbedtls_md_context_t ctx;
  mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;
  
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
  mbedtls_md_hmac_starts(&ctx, (const unsigned char *) key.c_str(), key.length());
  mbedtls_md_hmac_update(&ctx, (const unsigned char *) message.c_str(), message.length());
  mbedtls_md_hmac_finish(&ctx, hmacResult);
  mbedtls_md_free(&ctx);
  
  String sig = "";
  for (int i = 0; i < 32; i++) {
    char str[3];
    sprintf(str, "%02x", hmacResult[i]);
    sig += str;
  }
  return sig;
}

// ==========================================================
// HÀM GỬI POST XÁC THỰC VÂN TAY (CHECK IN / CHECK OUT)
// ==========================================================
void sendFingerprintCheck(int fingerID) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected. Cannot send API request.");
    return;
  }
  
  HTTPClient http;
  String url = api_base_url + "/users/fingerprint";
  
  String fingerprint_id = "FINGER_" + String(fingerID);
  String body = "{\"fingerprint_id\":\"" + fingerprint_id + "\"}";
  
  String timestamp = String(time(nullptr));
  String signatureMessage = body + timestamp;
  String signature = calculateHMAC(signatureMessage, HMAC_SECRET);
  
  WiFiClientSecure clientSecure;
  WiFiClient clientNormal;
  int httpResponseCode = -1;
  
  if (api_base_url.startsWith("https")) {
    clientSecure.setInsecure();
    http.begin(clientSecure, url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Signature", signature);
    http.addHeader("X-Timestamp", timestamp);
    Serial.print("Sending POST request to: ");
    Serial.println(url);
    httpResponseCode = http.POST(body);
  } else {
    http.begin(clientNormal, url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Signature", signature);
    http.addHeader("X-Timestamp", timestamp);
    Serial.print("Sending POST request to: ");
    Serial.println(url);
    httpResponseCode = http.POST(body);
  }
  
  lcd.clear();
  if (httpResponseCode == 200) {
    String response = http.getString();
    Serial.println("Response: " + response);
    
    JsonDocument doc;
    deserializeJson(doc, response);
    String name = doc["data"]["driver_name"] | "";
    String status = doc["data"]["status"] | "";
    String driver_id = doc["data"]["driver_id"] | "";
    
    if (name == "" || name == "null" || name == "None") {
      name = "Tai xe hop le";
    }
    
    lcdPrint(0, 0, name);
    if (status == "ACTIVE") {
      lcdPrint(0, 1, "Check-In OK");
    } else {
      lcdPrint(0, 1, "Check-Out OK");
    }

    // Phát quảng bá ESP-NOW thông tin tài xế
    DriverInfoMsg msg = {};
    memset(&msg, 0, sizeof(msg));
    strncpy(msg.driver_id, driver_id.c_str(), sizeof(msg.driver_id) - 1);
    strncpy(msg.driver_name, name.c_str(), sizeof(msg.driver_name) - 1);
    strncpy(msg.status, status.c_str(), sizeof(msg.status) - 1);
    
    uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    esp_err_t res = esp_now_send(broadcastAddress, (uint8_t*)&msg, sizeof(msg));
    if (res == ESP_OK) {
      Serial.printf("[ESP-NOW] Broadcast check-in/out: driver_id=%s, name=%s, status=%s\n", msg.driver_id, msg.driver_name, msg.status);
    } else {
      Serial.println("[ESP-NOW] Broadcast failed");
    }
  } else if (httpResponseCode == 404) {
    Serial.printf("Error 404: Fingerprint not registered to any user. Deleting local orphan ID #%d...\n", fingerID);
    finger.deleteModel(fingerID);
    lcdPrint(0, 0, "   CANH BAO!   ");
    lcdPrint(0, 1, "  VAN TAY LA!   ");
    myDFPlayer.playMp3Folder(2); // Báo âm thanh vân tay lạ
  } else {
    Serial.print("Error sending POST: ");
    Serial.println(httpResponseCode);
    lcdPrint(0, 0, "Loi ket noi!");
    lcdPrint(0, 1, "Code: " + String(httpResponseCode));
  }
  http.end();
}

// ==========================================================
// HÀM GỬI PATCH LIÊN KẾT VÂN TAY CHO TÀI XẾ (SAU KHI ENROLL)
// ==========================================================
bool sendFingerprintEnroll(String user_id, int fingerID) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected. Cannot send API request.");
    return false;
  }
  
  HTTPClient http;
  String url = api_base_url + "/users/" + user_id + "/fingerprint";
  
  String fingerprint_id = "FINGER_" + String(fingerID);
  String body = "{\"fingerprint_id\":\"" + fingerprint_id + "\"}";
  
  WiFiClientSecure clientSecure;
  WiFiClient clientNormal;
  int httpResponseCode = -1;
  
  if (api_base_url.startsWith("https")) {
    clientSecure.setInsecure();
    http.begin(clientSecure, url);
    http.addHeader("Content-Type", "application/json");
    Serial.print("Sending PATCH request to: ");
    Serial.println(url);
    httpResponseCode = http.PATCH(body);
  } else {
    http.begin(clientNormal, url);
    http.addHeader("Content-Type", "application/json");
    Serial.print("Sending PATCH request to: ");
    Serial.println(url);
    httpResponseCode = http.PATCH(body);
  }
  
  bool success = false;
  if (httpResponseCode == 200) {
    String response = http.getString();
    Serial.println("Response: " + response);
    success = true;
  } else {
    Serial.print("Error sending PATCH: ");
    Serial.println(httpResponseCode);
  }
  http.end();
  return success;
}

// ==========================================================
// HÀM GỬI BÁO CÁO KẾT QUẢ ENROLL LÊN MQTT
// ==========================================================
void sendEnrollResult(String user_id, String fingerprint_id, String error_msg) {
  if (!client.connected()) return;
  
  JsonDocument doc;
  if (fingerprint_id.length() > 0) {
    doc["status"] = "success";
    doc["user_id"] = user_id;
    doc["fingerprint_id"] = fingerprint_id;
  } else {
    doc["status"] = "failed";
    doc["user_id"] = user_id;
    doc["reason"] = error_msg;
  }
  
  char buffer[256];
  serializeJson(doc, buffer);
  client.publish(MQTT_TOPIC_ENROLL_RESULT, buffer);
  Serial.print("Published enroll result: ");
  Serial.println(buffer);
}

// ==========================================================
// HÀM TÌM SLOT CÒN TRỐNG TRONG CẢM BIẾN VÂN TAY
// ==========================================================
uint8_t getFirstEmptyID() {
  for (uint8_t id = 1; id <= 127; id++) {
    if (finger.loadModel(id) != FINGERPRINT_OK) {
      return id; // Slot trống
    }
  }
  return 0; // Đầy bộ nhớ
}

// ==========================================================
// QUY TRÌNH ĐĂNG KÝ VÂN TAY (2 LẦN ĐẶT NGÓN TAY VÀ LƯU)
// ==========================================================
uint8_t getFingerprintEnroll(int id) {
  int p = -1;
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Enroll ID: #");
  lcd.print(id);
  lcd.setCursor(0, 1);
  lcd.print("Dat ngon tay...");
  Serial.print("Waiting for valid finger to enroll as #"); Serial.println(id);
  
  // Vòng lặp chờ đặt vân tay lần 1
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    if (p == FINGERPRINT_OK) {
      Serial.println("Image taken");
    } else if (p == FINGERPRINT_NOFINGER) {
      // Đang chờ ngón tay
    } else {
      Serial.print("Error code: "); Serial.println(p);
    }
    delay(50);
    client.loop(); // Duy trì kết nối MQTT
  }

  p = finger.image2Tz(1);
  if (p != FINGERPRINT_OK) {
    Serial.println("Image 1 failed to convert");
    return p;
  }
  
  // KIỂM TRA TRÙNG LẶP: Tìm xem vân tay này đã được lưu ở slot nào chưa
  int search_p = finger.fingerSearch();
  if (search_p == FINGERPRINT_OK) {
    uint8_t existing_id = finger.fingerID;
    Serial.printf("[Enroll] Fingerprint already exists in sensor at slot #%d. Deleting to prevent duplicates...\n", existing_id);
    finger.deleteModel(existing_id);
    Serial.printf("[Enroll] Deleted duplicate slot #%d.\n", existing_id);
  }
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Nhac ngon tay ra");
  Serial.println("Remove finger");
  delay(2000);
  p = 0;
  while (p != FINGERPRINT_NOFINGER) {
    p = finger.getImage();
    delay(50);
    client.loop();
  }
  
  p = -1;
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Dat lai ngon tay");
  lcd.setCursor(0, 1);
  lcd.print("lan 2...");
  Serial.println("Place the same finger again");
  
  // Vòng lặp chờ đặt vân tay lần 2
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    if (p == FINGERPRINT_OK) {
      Serial.println("Image 2 taken");
    }
    delay(50);
    client.loop();
  }

  p = finger.image2Tz(2);
  if (p != FINGERPRINT_OK) {
    Serial.println("Image 2 failed to convert");
    return p;
  }
  
  Serial.print("Creating model for #");  Serial.println(id);
  p = finger.createModel();
  if (p != FINGERPRINT_OK) {
    Serial.print("❌ Fingerprints did not match or failed. Error code: 0x");
    Serial.println(p, HEX);
    return p;
  }
  
  p = finger.storeModel(id);
  if (p == FINGERPRINT_OK) {
    Serial.println("Stored successfully!");
  } else {
    Serial.println("Error storing model");
    return p;
  }
  return FINGERPRINT_OK;
}

// ==========================================================
// HÀM ĐIỀU PHỐI ĐĂNG KÝ VÂN TAY KHI CÓ MQTT COMMAND
// ==========================================================
void handleEnrollment() {
  uint8_t nextId = getFirstEmptyID();
  if (nextId == 0) {
    Serial.println("Error: No empty fingerprint slot left!");
    sendEnrollResult(targetEnrollUserId, "", "Sensor memory full");
    isEnrolling = false;
    hienThiManHinhCho();
    return;
  }
  
  // Chờ người dùng nhấc ngón tay ra trước khi bắt đầu đăng ký
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Chuan bi dang ky");
  lcd.setCursor(0, 1);
  lcd.print("Vui long cho...");
  delay(1000);
  while (finger.getImage() != FINGERPRINT_NOFINGER) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Nhac ngon tay ra");
    lcd.setCursor(0, 1);
    lcd.print("Khoi cam bien...");
    delay(500);
    client.loop(); // Duy trì MQTT
  }
  
  bool enrollSuccess = false;
  uint8_t res = -1;
  
  // Cho phép thử tối đa 3 lần trước khi báo lỗi về server
  for (int attempt = 1; attempt <= 3; attempt++) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Enroll ID: #");
    lcd.print(nextId);
    lcd.setCursor(0, 1);
    lcd.print("Lan thu: ");
    lcd.print(attempt);
    lcd.print("/3");
    delay(2000);
    
    res = getFingerprintEnroll(nextId);
    if (res == FINGERPRINT_OK) {
      enrollSuccess = true;
      break;
    } else {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Thu lai...");
      lcd.setCursor(0, 1);
      lcd.print("Ma loi: 0x");
      lcd.print(res, HEX);
      
      // Chờ người dùng nhấc ngón tay ra trước khi thử lại
      Serial.println("Waiting for finger release before next attempt...");
      delay(1000);
      while (finger.getImage() != FINGERPRINT_NOFINGER) {
        delay(50);
        client.loop();
      }
      delay(1000);
    }
  }
  
  if (enrollSuccess) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Enroll Success!");
    lcd.setCursor(0, 1);
    lcd.print("ID: #");
    lcd.print(nextId);
    
    // Loa phát file 0001.mp3 (Vân tay thành công)
    myDFPlayer.playMp3Folder(1);
    
    // Gọi API cập nhật lên server
    bool apiSuccess = sendFingerprintEnroll(targetEnrollUserId, nextId);
    if (apiSuccess) {
      sendEnrollResult(targetEnrollUserId, "FINGER_" + String(nextId), "");
    } else {
      sendEnrollResult(targetEnrollUserId, "", "API Update failed");
    }
    
    delay(4000);
  } else {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Enroll Failed!");
    lcd.setCursor(0, 1);
    lcd.print("Da thu 3 lan");
    
    // Loa phát file 0002.mp3 (Vân tay lạ/báo lỗi) để phản hồi thất bại bằng còi cảnh báo
    myDFPlayer.playMp3Folder(2);
    
    // Trả kết quả lỗi về server/MQTT sau 3 lần thử thất bại
    sendEnrollResult(targetEnrollUserId, "", "Fingerprint mismatch or sensor error after 3 attempts");
    delay(3000);
  }
  
  // Chờ người dùng nhấc ngón tay ra trước khi chuyển sang chế độ quét bình thường
  Serial.println("Waiting for finger release before resuming normal loop...");
  delay(1000); // Đợi 1 giây để người dùng bắt đầu nhấc tay
  while (finger.getImage() != FINGERPRINT_NOFINGER) {
    delay(50);
    client.loop(); // Duy trì MQTT
  }
  Serial.println("Finger released. Resuming normal loop.");
  
  isEnrolling = false;
  hienThiManHinhCho();
}

// ==========================================================
// HÀM XỬ LÝ QUÉT VÂN TAY THỦ CÔNG & ĐIỂM DANH ĐỒNG BỘ
// ==========================================================
void checkFingerprintAndDisplay()
{
  uint8_t p = finger.getImage();

  if (p != FINGERPRINT_OK)
    return;

  Serial.println("\n🔍 Phát hiện vân tay! Đang xử lý mẫu...");
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Dang quet mau...");
  lcd.setCursor(0, 1);
  lcd.print("Vui long cho...");

  p = finger.image2Tz();
  if (p != FINGERPRINT_OK)
  {
    Serial.println("⚠️ Ảnh quét bị mờ.");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("ANH QUA MO!     ");
    lcd.setCursor(0, 1);
    lcd.print("Vui long quet lai");
    delay(2000);
    hienThiManHinhCho();
    return;
  }

  p = finger.fingerSearch();
  lcd.clear();

  if (p == FINGERPRINT_OK)
  {
    // TRƯỜNG HỢP 1: TÀI XẾ HỢP LỆ (Check-in / Check-out thành công)
    Serial.print("🎉 SUCCESS! Đăng nhập thành công. ID Tài xế: #");
    Serial.println(finger.fingerID);

    lcdPrint(0, 0, "  SUCCESS!  ");
    lcdPrint(0, 1, "Tai xe ID: #" + String(finger.fingerID));

    // Loa phát file 0001.mp3 (Thành công)
    myDFPlayer.playMp3Folder(1);

    // Gửi tín hiệu điểm danh lên Backend API
    sendFingerprintCheck(finger.fingerID);

    delay(4000); 
  }
  else if (p == FINGERPRINT_NOTFOUND)
  {
    // TRƯỜNG HỢP 2: VÂN TAY LẠ (Cảnh báo an ninh)
    Serial.println("🚨 CANH BAO: Phat hien van tay la!");

    lcdPrint(0, 0, "   CANH BAO!   ");
    lcdPrint(0, 1, "  VAN TAY LA!   ");

    // Loa phát file 0002.mp3 (Vân tay lạ)
    myDFPlayer.playMp3Folder(2);

    delay(4000); 
  }
  else
  {
    Serial.println("❌ Lỗi cấu trúc truyền dữ liệu.");
    lcdPrint(0, 0, "Loi he thong!");
    delay(2000);
  }

  hienThiManHinhCho();
}

// ==========================================================
// HÀM HIỂN THỊ MÀN HÌNH CHỜ MẶC ĐỊNH
// ==========================================================
void hienThiManHinhCho()
{
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("  ROAD SENTINEL ");
  lcd.setCursor(0, 1);
  lcd.print("Moi quet van tay");
}

// ==========================================================
// CALLBACK XỬ LÝ MESSAGE NHẬN ĐƯỢC TỪ MQTT BROKER
// ==========================================================
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, message);
  if (error) {
    Serial.print("deserializeJson() failed: ");
    Serial.println(error.c_str());
    return;
  }

  String topicStr = String(topic);
  
  // 1. Nhận sự kiện Alert từ AI Model của hệ thống
  if (topicStr.startsWith("roadsentinel/alerts/")) {
    String event = doc["event"];
    if (event == "normal") {
      Serial.println("System normal. Stopping alerts.");
      myDFPlayer.stop(); // Tắt còi/loa cảnh báo
      hienThiManHinhCho();
    } else if (event == "sleeping" || event == "drowsy") {
      Serial.println("Alert: Sleeping/Drowsy -> 0003.mp3");
      lcd.clear();
      lcdPrint(0, 0, "   CANH BAO!   ");
      lcdPrint(0, 1, "    NGU GAT!    ");
      myDFPlayer.playMp3Folder(3); // 0003.mp3
    } else if (event == "using_phone") {
      Serial.println("Alert: Using Phone -> 0004.mp3");
      lcd.clear();
      lcdPrint(0, 0, "   CANH BAO!   ");
      lcdPrint(0, 1, " DIEN THOAI DI DONG");
      myDFPlayer.playMp3Folder(4); // 0004.mp3
    } else if (event == "distracted") {
      Serial.println("Alert: Distracted -> 0005.mp3");
      lcd.clear();
      lcdPrint(0, 0, "   CANH BAO!   ");
      lcdPrint(0, 1, " MAT TAP TRUNG! ");
      myDFPlayer.playMp3Folder(5); // 0005.mp3
    }
  }
  // 2. Nhận lệnh Enroll hoặc Clear vân tay
  else if (topicStr.equals(MQTT_TOPIC_ENROLL)) {
    String command = doc["command"] | "";
    if (command == "clear_all") {
      Serial.println("MQTT commanded: Clearing all fingerprints from sensor!");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Xoa tat ca...");
      lcd.setCursor(0, 1);
      lcd.print("Vui long cho...");
      
      if (finger.emptyDatabase() == FINGERPRINT_OK) {
        Serial.println("Fingerprint database cleared successfully!");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("  RESET DEVICE  ");
        lcd.setCursor(0, 1);
        lcd.print("Xoa thanh cong! ");
      } else {
        Serial.println("Failed to clear fingerprint database!");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("  RESET DEVICE  ");
        lcd.setCursor(0, 1);
        lcd.print("Xoa that bai!   ");
      }
      delay(3000);
      hienThiManHinhCho();
    } else {
      String user_id = doc["user_id"];
      if (user_id.length() > 0) {
        Serial.print("Enrolling fingerprint for user: ");
        Serial.println(user_id);
        isEnrolling = true;
        targetEnrollUserId = user_id;
      }
    }
  }
}

// ==========================================================
// HÀM DUY TRÌ & KẾT NỐI LẠI MQTT
// ==========================================================
void reconnectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;
  
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Connecting MQTT");
    
    String clientId = "RoadSentinelDevice-" + String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)) {
      Serial.println("connected");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("MQTT Connected!");
      delay(1000);
      
      client.subscribe(MQTT_TOPIC_ALERTS);
      client.subscribe(MQTT_TOPIC_ENROLL);
      
      hienThiManHinhCho();
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("MQTT Error: ");
      lcd.print(client.state());
      
      delay(5000);
    }
  }
}