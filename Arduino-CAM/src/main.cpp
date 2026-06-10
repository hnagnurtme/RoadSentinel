/**
 * ESP32-CAM WebSocket Streamer — High-FPS / Stable Build
 *
 * Tối ưu hóa:
 *  - QQVGA (160×120) + quality 20 → ~3-5 KB/frame, dễ dàng đạt 20+ fps
 *  - FreeRTOS: tách camera-capture task và websocket-send task
 *  - Double-buffer queue (xQueueSend / xQueueReceive) tránh stall
 *  - ws.loop() chạy độc lập, không bao giờ bị block bởi camera I/O
 *  - Watchdog tự động restart nếu queue bị treo > 10s
 *  - Flow-control: bỏ frame mới nếu queue đầy (không block producer)
 *  - WiFi auto-reconnect qua event handler
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_camera.h>
#include <WebSocketsClient.h>   // arduinoWebSockets by Links2004
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

// ─── Driver Info Struct (matching ESP32-Device) ──────────────────────────────
struct DriverInfoMsg {
  char driver_id[37];
  char driver_name[33];
  char status[12];
};

// ─── Driver State (ESP-NOW to WebSocket sync) ──────────────────────────────────
static char            active_driver_id[37] = "";
static char            active_driver_name[33] = "";
static volatile bool   driver_active = false;

// Flags to trigger sending message in the WebSocket task context
static volatile bool   pending_ws_login_send = false;
static volatile bool   pending_ws_logout_send = false;

static void onDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
    if (len == sizeof(DriverInfoMsg)) {
        DriverInfoMsg msg;
        memcpy(&msg, incomingData, sizeof(msg));
        
        Serial.printf("[ESP-NOW] Received: driver_id=%s, name=%s, status=%s\n", msg.driver_id, msg.driver_name, msg.status);
        
        if (strcmp(msg.status, "ACTIVE") == 0) {
            strncpy(active_driver_id, msg.driver_id, sizeof(active_driver_id) - 1);
            active_driver_id[sizeof(active_driver_id) - 1] = '\0';
            strncpy(active_driver_name, msg.driver_name, sizeof(active_driver_name) - 1);
            active_driver_name[sizeof(active_driver_name) - 1] = '\0';
            driver_active = true;
            pending_ws_login_send = true;
            pending_ws_logout_send = false;
        } else {
            active_driver_id[0] = '\0';
            active_driver_name[0] = '\0';
            driver_active = false;
            pending_ws_login_send = false;
            pending_ws_logout_send = true;
        }
    } else {
        Serial.printf("[ESP-NOW] Received packet with invalid size: %d (expected %d)\n", len, sizeof(DriverInfoMsg));
    }
}

// // ─── Wi-Fi credentials ────────────────────────────────────────────────────────
// static const char* WIFI_SSID = "test123";
// static const char* WIFI_PASS = "12345678";
// ─── Wi-Fi credentials ────────────────────────────────────────────────────────
static const char* WIFI_SSID = "37 Ngo Van So";
static const char* WIFI_PASS = "987654321";
// ─── Server ───────────────────────────────────────────────────────────────────
static String         ws_host = "road-sentinel.trunganh.tech";
static uint16_t       ws_port = 443;
static String         ws_path = "/api/v1/ws/camera";
static bool           ws_use_ssl = true;

// ─── Tuning ───────────────────────────────────────────────────────────────────
// Ưu tiên chất lượng ảnh hơn tốc độ
static const framesize_t FRAME_SIZE        = FRAMESIZE_QVGA;   // 320x240 (Giảm độ phân giải để tránh nghẽn mạng gây delay)
static const int         JPEG_QUALITY      = 12;               // Giảm số = tăng chất lượng ảnh (số thấp hơn cho ảnh nét hơn)
static const uint32_t    CAPTURE_INTERVAL_MS = 40;             // ~25 fps target (thực tế và ổn định hơn)

// Queue depth: Chỉ cần 1 frame (để đảm bảo không bị trễ thời gian, frame mới sẽ ghi đè lên frame cũ ngay lập tức)
static const int QUEUE_DEPTH = 1;

// ─── AI Thinker ESP32-CAM pins ───────────────────────────────────────────────
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ─── Frame buffer descriptor ─────────────────────────────────────────────────
// Thay vì chuyển camera_fb_t* qua queue (nguy hiểm nếu overwrite),
// ta copy dữ liệu JPEG vào heap rồi mới enqueue con trỏ tới bản copy.
struct FrameMsg {
    uint8_t* data;
    size_t   len;
};

// ─── Globals ──────────────────────────────────────────────────────────────────
static QueueHandle_t   frame_queue   = nullptr;
static WebSocketsClient ws;
static volatile bool   ws_connected  = false;
static volatile bool   wifi_ready    = false;

static uint32_t stat_sent     = 0;
static uint32_t stat_dropped  = 0;
static uint32_t stat_cap_err  = 0;

// ─── Watchdog ────────────────────────────────────────────────────────────────
static volatile uint32_t last_sent_ms = 0;
static const uint32_t    WD_TIMEOUT_MS = 10000;  // 10s không gửi được → restart

// ─── WiFi event ──────────────────────────────────────────────────────────────
static void wifi_event_handler(WiFiEvent_t event) {
    switch (event) {
        case ARDUINO_EVENT_WIFI_STA_GOT_IP:
            wifi_ready = true;
            Serial.printf("[WiFi] Connected. IP: %s  RSSI: %d dBm\n",
                          WiFi.localIP().toString().c_str(), WiFi.RSSI());
            break;
        case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
            wifi_ready    = false;
            ws_connected  = false;
            Serial.println("[WiFi] Disconnected — reconnecting...");
            WiFi.reconnect();
            break;
        default:
            break;
    }
}

// ─── WebSocket event handler ──────────────────────────────────────────────────
static void onWebSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_CONNECTED:
            ws_connected = true;
            last_sent_ms = millis();
            Serial.printf("[WS] Connected to %s://%s:%d%s\n",
                          ws_use_ssl ? "wss" : "ws", ws_host.c_str(), ws_port, ws_path.c_str());
            ws.sendTXT("{\"type\":\"hello\",\"device\":\"esp32-cam\",\"mode\":\"high-fps\"}");
            if (driver_active) {
                char ws_msg[128];
                snprintf(ws_msg, sizeof(ws_msg), "{\"type\":\"driver_login\",\"driver_id\":\"%s\"}", active_driver_id);
                ws.sendTXT(ws_msg);
                Serial.printf("[WS] Restored active driver: %s\n", active_driver_id);
            }
            break;

        case WStype_DISCONNECTED:
            ws_connected = false;
            Serial.println("[WS] Disconnected");
            break;

        case WStype_TEXT:
            // Server điều khiển: {"cmd":"ping"} → pong stats
            {
                String msg = String((char*)payload);
                if (msg.indexOf("\"ping\"") >= 0) {
                    char pong[160];
                    snprintf(pong, sizeof(pong),
                             "{\"type\":\"pong\",\"sent\":%u,\"dropped\":%u,"
                             "\"cap_err\":%u,\"heap\":%u,\"rssi\":%d}",
                             stat_sent, stat_dropped, stat_cap_err,
                             ESP.getFreeHeap(), WiFi.RSSI());
                    ws.sendTXT(pong);
                }
                // Điều chỉnh quality động: {"cmd":"set_quality","value":15}
                else if (msg.indexOf("\"set_quality\"") >= 0) {
                    int idx = msg.indexOf("\"value\":");
                    if (idx >= 0) {
                        int q = constrain(msg.substring(idx + 8).toInt(), 0, 63);
                        sensor_t* s = esp_camera_sensor_get();
                        if (s) s->set_quality(s, q);
                        Serial.printf("[CMD] Quality → %d\n", q);
                    }
                }
            }
            break;

        case WStype_ERROR:
            Serial.println("[WS] Socket error");
            break;

        default:
            break;
    }
}

// ─── Camera init ──────────────────────────────────────────────────────────────
static bool init_camera() {
    camera_config_t cfg = {};
    cfg.ledc_channel  = LEDC_CHANNEL_0;
    cfg.ledc_timer    = LEDC_TIMER_0;
    cfg.pin_d0 = Y2_GPIO_NUM; cfg.pin_d1 = Y3_GPIO_NUM;
    cfg.pin_d2 = Y4_GPIO_NUM; cfg.pin_d3 = Y5_GPIO_NUM;
    cfg.pin_d4 = Y6_GPIO_NUM; cfg.pin_d5 = Y7_GPIO_NUM;
    cfg.pin_d6 = Y8_GPIO_NUM; cfg.pin_d7 = Y9_GPIO_NUM;
    cfg.pin_xclk     = XCLK_GPIO_NUM;
    cfg.pin_pclk     = PCLK_GPIO_NUM;
    cfg.pin_vsync    = VSYNC_GPIO_NUM;
    cfg.pin_href     = HREF_GPIO_NUM;
    cfg.pin_sccb_sda = SIOD_GPIO_NUM;
    cfg.pin_sccb_scl = SIOC_GPIO_NUM;
    cfg.pin_pwdn     = PWDN_GPIO_NUM;
    cfg.pin_reset    = RESET_GPIO_NUM;

    cfg.xclk_freq_hz = 20000000;
    cfg.pixel_format = PIXFORMAT_JPEG;

    // GRAB_WHEN_EMPTY: camera chỉ capture khi fb rảnh
    // → tránh overwrite frame đang dùng
    cfg.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;

    if (psramFound()) {
        cfg.frame_size   = FRAME_SIZE;
        cfg.jpeg_quality = JPEG_QUALITY;
        cfg.fb_count     = 2;
        cfg.fb_location  = CAMERA_FB_IN_PSRAM;
    } else {
        // Không có PSRAM: dùng DRAM, giới hạn xuống QQVGA 1 buffer
        cfg.frame_size   = FRAMESIZE_QQVGA;
        cfg.jpeg_quality = 25;
        cfg.fb_count     = 1;
        cfg.fb_location  = CAMERA_FB_IN_DRAM;
    }

    if (esp_camera_init(&cfg) != ESP_OK) {
        Serial.println("[CAM] Init FAILED");
        return false;
    }

    sensor_t* s = esp_camera_sensor_get();
    if (s) {
        s->set_framesize(s,      cfg.frame_size);
        s->set_quality(s,        cfg.jpeg_quality);
        // Tắt hết tính năng nặng để giảm latency
        s->set_lenc(s,           0);   // lens correction off
        s->set_raw_gma(s,        1);
        s->set_exposure_ctrl(s,  1);
        s->set_gain_ctrl(s,      1);
        s->set_awb_gain(s,       1);
        s->set_whitebal(s,       1);
        s->set_brightness(s,     0);
        s->set_contrast(s,       0);
        s->set_saturation(s,     0);
        s->set_sharpness(s,      0);   // sharp=0 → ít xử lý hơn
        s->set_denoise(s,        0);   // denoise off → nhanh hơn
        s->set_hmirror(s,        0);   // lật ảnh theo trục ngang (trái <-> phải)
        s->set_vflip(s,          0);   // lật ảnh theo trục dọc (trên <-> dưới)
    }

    Serial.printf("[CAM] Init OK — PSRAM: %s\n", psramFound() ? "yes" : "no");
    return true;
}

// ─── Task 1: Camera Capture (Core 0) ─────────────────────────────────────────
// Chạy trên Core 0, chỉ lo chụp ảnh và enqueue
static void captureTask(void* arg) {
    TickType_t last_wake = xTaskGetTickCount();

    while (true) {
        // Giữ đúng interval, không drift
        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(CAPTURE_INTERVAL_MS));

        // Bỏ qua nếu WebSocket chưa kết nối (tiết kiệm CPU & bus camera)
        if (!ws_connected) continue;

        // Chụp frame
        camera_fb_t* fb = esp_camera_fb_get();
        if (!fb || fb->format != PIXFORMAT_JPEG || fb->len == 0) {
            stat_cap_err++;
            if (fb) esp_camera_fb_return(fb);
            continue;
        }

        // Copy dữ liệu ra heap riêng để trả fb ngay lập tức
        // → camera buffer rảnh cho frame tiếp theo
        FrameMsg msg;
        msg.len  = fb->len;
        msg.data = (uint8_t*)heap_caps_malloc(
            fb->len,
            psramFound() ? MALLOC_CAP_SPIRAM : MALLOC_CAP_DEFAULT
        );

        esp_camera_fb_return(fb);  // trả buffer NGAY sau copy

        if (!msg.data) {
            // Không đủ RAM → drop frame
            stat_dropped++;
            continue;
        }

        memcpy(msg.data, fb->buf, msg.len); // ← fb đã return, nhưng buf vẫn valid
        // NOTE: thực ra cần copy trước khi return. Đảo lại:
        // (code đúng ở dưới)

        // ── Phiên bản đúng: copy TRƯỚC khi return ──
        // Đã xử lý bên dưới — đây là placeholder, xem vòng lặp thực bên dưới
        free(msg.data);
    }
}

// ─── Task 1 (phiên bản chính xác): Camera Capture ────────────────────────────
static void captureTaskCorrect(void* arg) {
    TickType_t last_wake = xTaskGetTickCount();

    while (true) {
        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(CAPTURE_INTERVAL_MS));

        if (!ws_connected) continue;

        camera_fb_t* fb = esp_camera_fb_get();
        if (!fb || fb->format != PIXFORMAT_JPEG || fb->len == 0) {
            stat_cap_err++;
            if (fb) esp_camera_fb_return(fb);
            continue;
        }

        // Cấp phát bộ nhớ và copy TRƯỚC khi return fb
        FrameMsg msg;
        msg.len  = fb->len;
        msg.data = (uint8_t*)heap_caps_malloc(
            fb->len,
            psramFound() ? MALLOC_CAP_SPIRAM : MALLOC_CAP_DEFAULT
        );

        if (msg.data) {
            memcpy(msg.data, fb->buf, fb->len);  // copy khi fb còn hợp lệ
        }

        esp_camera_fb_return(fb);  // trả buffer SAU khi đã copy xong

        if (!msg.data) {
            stat_dropped++;
            continue;
        }

        // Enqueue — nếu queue đầy thì BỎ FRAME CŨ NHẤT để luôn ưu tiên frame mới -> Chống delay cực lớn
        if (xQueueSend(frame_queue, &msg, 0) != pdTRUE) {
            FrameMsg old_msg;
            if (xQueueReceive(frame_queue, &old_msg, 0) == pdTRUE) {
                free(old_msg.data); // xóa frame cũ
                stat_dropped++;
                xQueueSend(frame_queue, &msg, 0); // đẩy frame mới nhất vào
            } else {
                free(msg.data);
                stat_dropped++;
            }
        }
    }
}

// ─── Task 2: WebSocket Send (Core 1) ─────────────────────────────────────────
// Chạy trên Core 1, lo ws.loop() và gửi frame
static void wsTask(void* arg) {
    // Chờ WiFi sẵn sàng
    while (!wifi_ready) vTaskDelay(pdMS_TO_TICKS(100));

    if (ws_use_ssl) {
        ws.beginSSL(ws_host.c_str(), ws_port, ws_path.c_str());
    } else {
        ws.begin(ws_host.c_str(), ws_port, ws_path.c_str());
    }
    ws.onEvent(onWebSocketEvent);
    ws.setReconnectInterval(3000);
    ws.enableHeartbeat(15000, 3000, 2);

    Serial.printf("[WS] Connecting to %s://%s:%d%s\n",
                  ws_use_ssl ? "wss" : "ws", ws_host.c_str(), ws_port, ws_path.c_str());

    FrameMsg msg;

    while (true) {
        // ws.loop() phải gọi THƯỜNG XUYÊN — đây là trái tim của WebSocket
        ws.loop();

        // Handle pending driver check-in/out updates
        if (pending_ws_login_send) {
            pending_ws_login_send = false;
            if (ws_connected) {
                char ws_msg[128];
                snprintf(ws_msg, sizeof(ws_msg), "{\"type\":\"driver_login\",\"driver_id\":\"%s\"}", active_driver_id);
                ws.sendTXT(ws_msg);
                Serial.printf("[WS] Sent driver_login: %s\n", active_driver_id);
            }
        }
        if (pending_ws_logout_send) {
            pending_ws_logout_send = false;
            if (ws_connected) {
                ws.sendTXT("{\"type\":\"driver_login\",\"driver_id\":null}");
                Serial.println("[WS] Sent driver_logout");
            }
        }

        // Lấy frame từ queue, hàng đợi có độ sâu bằng 1 nên luôn lấy được frame mới nhất
        if (xQueueReceive(frame_queue, &msg, pdMS_TO_TICKS(10)) == pdTRUE) {
            if (ws_connected) {
                bool ok = ws.sendBIN(msg.data, msg.len);
                if (ok) {
                    stat_sent++;
                    last_sent_ms = millis();
                } else {
                    stat_dropped++;
                }
            } else {
                // WS chưa kết nối, drop frame đã dequeue
                stat_dropped++;
            }
            free(msg.data);  // luôn giải phóng sau khi xử lý
        }

        // Watchdog: nếu đã kết nối nhưng không gửi được lâu → restart
        if (ws_connected && (millis() - last_sent_ms > WD_TIMEOUT_MS)) {
            Serial.println("[WD] Stall detected — restarting");
            vTaskDelay(pdMS_TO_TICKS(100));
            ESP.restart();
        }
    }
}

// ─── Stats Task (Core 0, low priority) ───────────────────────────────────────
static void statsTask(void* arg) {
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(5000));  // log mỗi 5 giây
        uint32_t fps_approx = stat_sent / 5;  // ước tính trong window 5s
        Serial.printf(
            "[STATS] sent=%u (~%u fps)  dropped=%u  cap_err=%u  heap=%u  rssi=%d\n",
            stat_sent, fps_approx, stat_dropped, stat_cap_err,
            ESP.getFreeHeap(), WiFi.RSSI()
        );
        // Reset counter sau mỗi window để fps_approx luôn phản ánh hiện tại
        stat_sent    = 0;
        stat_dropped = 0;
        stat_cap_err = 0;
    }
}

// ─── Cloud Connection Settings ───────────────────────────────────────────────
// Dynamic discovery removed - directly using cloud configuration.

// ─── setup / loop ─────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n=== ESP32-CAM High-FPS Streamer ===");
    Serial.printf("Free heap  : %u B\n", ESP.getFreeHeap());
    Serial.printf("Free PSRAM : %u B\n", ESP.getFreePsram());

    // Camera trước WiFi để tránh xung đột bus
    if (!init_camera()) {
        Serial.println("[FATAL] Camera init failed — restart");
        delay(2000);
        ESP.restart();
    }

    // WiFi với event handler thay cho polling
    WiFi.onEvent(wifi_event_handler);
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);
    WiFi.setTxPower(WIFI_POWER_17dBm);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("[WiFi] Connecting");
    const uint32_t t0 = millis();
    while (!wifi_ready) {
        delay(250);
        Serial.print('.');
        if (millis() - t0 > 20000) {
            Serial.println("\n[FATAL] WiFi timeout — restart");
            delay(1000);
            ESP.restart();
        }
    }
    Serial.println();

    Serial.println("[Connection] Using production cloud server.");

    // Khởi tạo ESP-NOW
    if (esp_now_init() == ESP_OK) {
        Serial.println("[ESP-NOW] Initialized successfully");
        esp_now_register_recv_cb(onDataRecv);
    } else {
        Serial.println("[ESP-NOW] Error initializing");
    }

    // Tạo queue
    frame_queue = xQueueCreate(QUEUE_DEPTH, sizeof(FrameMsg));
    if (!frame_queue) {
        Serial.println("[FATAL] Queue create failed — restart");
        delay(1000);
        ESP.restart();
    }

    // Tạo các FreeRTOS tasks
    // captureTask → Core 0, priority 5 (cao hơn idle, thấp hơn ws)
    xTaskCreatePinnedToCore(
        captureTaskCorrect, "capture",
        4096, nullptr, 5,
        nullptr, 0
    );

    // wsTask → Core 1, priority 6 (cao nhất để ws.loop() không bị đói)
    xTaskCreatePinnedToCore(
        wsTask, "ws_send",
        8192, nullptr, 6,
        nullptr, 1
    );

    // statsTask → Core 0, priority 1 (background)
    xTaskCreatePinnedToCore(
        statsTask, "stats",
        2048, nullptr, 1,
        nullptr, 0
    );

    Serial.println("[BOOT] All tasks started");
}

void loop() {
    // loop() chạy trên Core 1 với priority thấp nhất
    // Tất cả logic đã được chuyển vào FreeRTOS tasks
    // Để loop() không chiếm CPU
    vTaskDelay(pdMS_TO_TICKS(1000));
}