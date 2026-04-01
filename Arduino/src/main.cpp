#include <Arduino.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <WebSocketsClient.h>   // arduinoWebSockets by Links2004

// ─── Wi-Fi credentials ────────────────────────────────────────────────────────
static const char* WIFI_SSID = "37 Ngo Van So";
static const char* WIFI_PASS = "987654321";

// ─── FastAPI VPS ──────────────────────────────────────────────────────────────
// Đổi thành IP/domain VPS của bạn và port FastAPI
static const char*    WS_HOST = "192.168.1.32";
static const uint16_t WS_PORT = 8000;
static const char*    WS_PATH = "/ws/camera";   // endpoint WebSocket trên FastAPI

// ─── Tuning ───────────────────────────────────────────────────────────────────
static const framesize_t FRAME_SIZE    = FRAMESIZE_QVGA;
static const int         JPEG_QUALITY  = 12;           // 0=best, 63=worst
static const uint32_t    FRAME_INTERVAL_MS = 80;       // ~12.5 fps

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

// ─── Globals ──────────────────────────────────────────────────────────────────
static WebSocketsClient ws;
static bool             ws_connected = false;
static uint32_t         last_frame_ms = 0;
static uint32_t         frame_count   = 0;
static uint32_t         reconnect_count = 0;

void handleServerCommand(uint8_t* payload, size_t length);

// ─── WebSocket event handler ──────────────────────────────────────────────────
void onWebSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_CONNECTED:
            ws_connected = true;
            Serial.printf("[WS] Connected to %s:%d%s\n", WS_HOST, WS_PORT, WS_PATH);
            // Gửi hello JSON để FastAPI nhận diện nguồn
            ws.sendTXT("{\"type\":\"hello\",\"device\":\"esp32-cam\"}");
            break;

        case WStype_DISCONNECTED:
            ws_connected = false;
            reconnect_count++;
            Serial.printf("[WS] Disconnected (reconnect #%u)\n", reconnect_count);
            break;

        case WStype_TEXT:
            // FastAPI có thể gửi lệnh điều khiển dạng JSON
            // Ví dụ: {"cmd":"set_quality","value":8} hoặc {"cmd":"set_fps","value":15}
            Serial.printf("[WS] Server msg: %s\n", (char*)payload);
            handleServerCommand(payload, length);
            break;

        case WStype_BIN:
            // Không dùng binary từ server trong flow này
            break;

        case WStype_ERROR:
            Serial.println("[WS] Error");
            break;

        case WStype_PING:
        case WStype_PONG:
            break;
    }
}

// ─── Xử lý lệnh từ FastAPI ───────────────────────────────────────────────────
// FastAPI có thể remote-control camera (chất lượng, fps, flip...)
void handleServerCommand(uint8_t* payload, size_t length) {
    // Parse JSON tối giản không dùng lib nặng
    String msg = String((char*)payload);

    if (msg.indexOf("\"set_quality\"") >= 0) {
        int idx = msg.indexOf("\"value\":");
        if (idx >= 0) {
            int q = msg.substring(idx + 8).toInt();
            q = constrain(q, 0, 63);
            sensor_t* s = esp_camera_sensor_get();
            if (s) s->set_quality(s, q);
            Serial.printf("[CMD] Quality set to %d\n", q);
        }
    }
    else if (msg.indexOf("\"set_framesize\"") >= 0) {
        int idx = msg.indexOf("\"value\":");
        if (idx >= 0) {
            int fs = msg.substring(idx + 8).toInt();
            sensor_t* s = esp_camera_sensor_get();
            if (s) s->set_framesize(s, (framesize_t)fs);
            Serial.printf("[CMD] Framesize set to %d\n", fs);
        }
    }
    else if (msg.indexOf("\"set_vflip\"") >= 0) {
        bool flip = msg.indexOf("\"value\":1") >= 0;
        sensor_t* s = esp_camera_sensor_get();
        if (s) s->set_vflip(s, flip ? 1 : 0);
    }
    else if (msg.indexOf("\"set_hmirror\"") >= 0) {
        bool mirror = msg.indexOf("\"value\":1") >= 0;
        sensor_t* s = esp_camera_sensor_get();
        if (s) s->set_hmirror(s, mirror ? 1 : 0);
    }
    else if (msg.indexOf("\"ping\"") >= 0) {
        // Trả lời pong với stats
        char pong[128];
        snprintf(pong, sizeof(pong),
                 "{\"type\":\"pong\",\"frames\":%u,\"heap\":%u,\"rssi\":%d}",
                 frame_count, ESP.getFreeHeap(), WiFi.RSSI());
        ws.sendTXT(pong);
    }
}

// ─── Gửi 1 frame JPEG qua WebSocket binary ───────────────────────────────────
static bool send_frame() {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("[CAM] fb_get failed");
        return false;
    }

    bool ok = false;
    if (fb->format == PIXFORMAT_JPEG) {
        // Gửi raw binary — FastAPI nhận bằng websocket.receive_bytes()
        ok = ws.sendBIN(fb->buf, fb->len);
    } else {
        // Trường hợp format không phải JPEG (hiếm khi xảy ra)
        Serial.println("[CAM] Non-JPEG frame, skipping");
        ok = true;  // không lỗi, chỉ skip
    }

    esp_camera_fb_return(fb);
    return ok;
}

// ─── Camera init ──────────────────────────────────────────────────────────────
static bool init_camera() {
    camera_config_t cfg = {};
    cfg.ledc_channel  = LEDC_CHANNEL_0;
    cfg.ledc_timer    = LEDC_TIMER_0;
    cfg.pin_d0        = Y2_GPIO_NUM;
    cfg.pin_d1        = Y3_GPIO_NUM;
    cfg.pin_d2        = Y4_GPIO_NUM;
    cfg.pin_d3        = Y5_GPIO_NUM;
    cfg.pin_d4        = Y6_GPIO_NUM;
    cfg.pin_d5        = Y7_GPIO_NUM;
    cfg.pin_d6        = Y8_GPIO_NUM;
    cfg.pin_d7        = Y9_GPIO_NUM;
    cfg.pin_xclk      = XCLK_GPIO_NUM;
    cfg.pin_pclk      = PCLK_GPIO_NUM;
    cfg.pin_vsync     = VSYNC_GPIO_NUM;
    cfg.pin_href      = HREF_GPIO_NUM;
    cfg.pin_sccb_sda  = SIOD_GPIO_NUM;
    cfg.pin_sccb_scl  = SIOC_GPIO_NUM;
    cfg.pin_pwdn      = PWDN_GPIO_NUM;
    cfg.pin_reset     = RESET_GPIO_NUM;
    cfg.xclk_freq_hz  = 20000000;
    cfg.pixel_format  = PIXFORMAT_JPEG;
    cfg.grab_mode     = CAMERA_GRAB_LATEST;
    cfg.fb_location   = CAMERA_FB_IN_PSRAM;

    if (psramFound()) {
        cfg.frame_size   = FRAME_SIZE;
        cfg.jpeg_quality = JPEG_QUALITY;
        cfg.fb_count     = 2;
    } else {
        cfg.frame_size   = FRAMESIZE_QVGA;
        cfg.jpeg_quality = 16;
        cfg.fb_count     = 1;
        cfg.fb_location  = CAMERA_FB_IN_DRAM;
    }

    if (esp_camera_init(&cfg) != ESP_OK) {
        Serial.println("[CAM] Init failed");
        return false;
    }

    sensor_t* s = esp_camera_sensor_get();
    if (s) {
        s->set_framesize(s,     psramFound() ? FRAME_SIZE : FRAMESIZE_QVGA);
        s->set_quality(s,       psramFound() ? JPEG_QUALITY : 16);
        s->set_brightness(s,    0);
        s->set_contrast(s,      1);
        s->set_saturation(s,    0);
        s->set_sharpness(s,     2);
        s->set_denoise(s,       1);
        s->set_ae_level(s,      1);
        s->set_awb_gain(s,      1);
        s->set_whitebal(s,      1);
        s->set_exposure_ctrl(s, 1);
        s->set_gain_ctrl(s,     1);
        s->set_lenc(s,          1);
        s->set_hmirror(s,       0);
        s->set_vflip(s,         0);
    }
    Serial.println("[CAM] Init OK");
    return true;
}

// ─── Wi-Fi ────────────────────────────────────────────────────────────────────
static bool connect_wifi() {
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);
    WiFi.setTxPower(WIFI_POWER_17dBm);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    Serial.print("[WiFi] Connecting");
    const uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED) {
        delay(250);
        Serial.print('.');
        if (millis() - t0 > 20000) {
            Serial.println("\n[WiFi] Timeout");
            return false;
        }
    }
    Serial.printf("\n[WiFi] Connected. IP: %s  RSSI: %d dBm\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
    return true;
}

// ─── WebSocket setup ─────────────────────────────────────────────────────────
static void setup_websocket() {
    // Dùng plain WS (ws://). Nếu VPS có SSL thì đổi sang beginSSL()
    ws.begin(WS_HOST, WS_PORT, WS_PATH);
    ws.onEvent(onWebSocketEvent);

    // Tự động reconnect mỗi 3 giây khi mất kết nối
    ws.setReconnectInterval(3000);

    // Heartbeat ping mỗi 15s, timeout 3s
    ws.enableHeartbeat(15000, 3000, 2);

    Serial.printf("[WS] Connecting to ws://%s:%d%s\n", WS_HOST, WS_PORT, WS_PATH);
}

// ─── Arduino entry points ─────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n=== ESP32-CAM WebSocket Client ===");
    Serial.printf("Free heap  : %u B\n", ESP.getFreeHeap());
    Serial.printf("Free PSRAM : %u B\n", ESP.getFreePsram());

    if (!init_camera()) {
        Serial.println("Camera error — restarting");
        delay(2000); ESP.restart();
    }
    if (!connect_wifi()) {
        Serial.println("WiFi error — restarting");
        delay(2000); ESP.restart();
    }

    setup_websocket();
}

void loop() {
    // Xử lý WebSocket events (reconnect, heartbeat, incoming msg)
    ws.loop();

    // Chỉ gửi frame khi đã kết nối và đủ interval
    if (ws_connected) {
        uint32_t now = millis();
        if (now - last_frame_ms >= FRAME_INTERVAL_MS) {
            if (send_frame()) {
                frame_count++;
            }
            last_frame_ms = now;

            // Log mỗi 100 frames
            if (frame_count % 100 == 0) {
                Serial.printf("[STATS] Frames: %u  Heap: %u  RSSI: %d\n",
                              frame_count, ESP.getFreeHeap(), WiFi.RSSI());
            }
        }
    }
}