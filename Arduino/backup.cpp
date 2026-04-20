#include <Arduino.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <WebSocketsClient.h>   // arduinoWebSockets by Links2004

// ─── Wi-Fi credentials ────────────────────────────────────────────────────────
static const char*    WIFI_SSID           = "ITF Da Nang";
static const char*    WIFI_PASS           = "itfdanang";

// ─── FastAPI VPS ──────────────────────────────────────────────────────────────
static const char*    WS_HOST             = "172.31.98.3";
static const uint16_t WS_PORT             = 8000;
static const char*    WS_PATH             = "/ws/camera";

// ─── Camera tuning ────────────────────────────────────────────────────────────
static const framesize_t FRAME_SIZE       = FRAMESIZE_QVGA;
static const int      JPEG_QUALITY_PSRAM  = 12;
static const int      JPEG_QUALITY_DRAM   = 16;
static const uint32_t FRAME_INTERVAL_MS   = 80;        // ~12.5 fps
static const uint32_t FB_GET_TIMEOUT_MS   = 500;       // max wait per frame
static const uint32_t CAM_WARMUP_FRAMES   = 15;        // flush sau init
static const uint32_t CAM_WARMUP_DELAY_MS = 100;
static const uint8_t  CAM_FAIL_REINIT     = 10;        // reinit sau N fail liên tiếp

// ─── WebSocket tuning ─────────────────────────────────────────────────────────
static const uint32_t WIFI_TIMEOUT_MS     = 20000;
static const uint32_t WS_RECONNECT_MS     = 3000;
static const uint32_t WS_HEARTBEAT_MS     = 15000;
static const uint32_t WS_HEARTBEAT_TO_MS  = 3000;
static const uint8_t  WS_HEARTBEAT_RETRY  = 2;

// ─── Logging ──────────────────────────────────────────────────────────────────
static const uint32_t LOG_EVERY_N_FRAMES  = 100;

// ─── AI Thinker ESP32-CAM pin map ────────────────────────────────────────────
#define PWDN_GPIO_NUM   32
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM    0
#define SIOD_GPIO_NUM   26
#define SIOC_GPIO_NUM   27
#define Y9_GPIO_NUM     35
#define Y8_GPIO_NUM     34
#define Y7_GPIO_NUM     39
#define Y6_GPIO_NUM     36
#define Y5_GPIO_NUM     21
#define Y4_GPIO_NUM     19
#define Y3_GPIO_NUM     18
#define Y2_GPIO_NUM      5
#define VSYNC_GPIO_NUM  25
#define HREF_GPIO_NUM   23
#define PCLK_GPIO_NUM   22

// ─── State ────────────────────────────────────────────────────────────────────
static WebSocketsClient ws;
static volatile bool    ws_connected  = false;
static uint32_t         last_frame_ms = 0;
static uint32_t         frame_count   = 0;
static uint32_t         fb_fail_count = 0;
static uint32_t         conn_count    = 0;

// ─── Forward declarations ─────────────────────────────────────────────────────
static bool init_camera();
static bool connect_wifi();
static void setup_websocket();
static bool send_frame();
static void warmup_camera();
static void reinit_camera();
static void handle_server_cmd(const String& msg);
static void send_pong();
static void print_stats();

// =============================================================================
// WebSocket event handler
// =============================================================================

void onWebSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_CONNECTED:
            ws_connected = true;
            conn_count++;
            Serial.printf("[WS] Connected  ws://%s:%d%s  (#%u)\n",
                          WS_HOST, WS_PORT, WS_PATH, conn_count);
            ws.sendTXT("{\"type\":\"hello\",\"device\":\"esp32-cam\"}");
            break;

        case WStype_DISCONNECTED:
            ws_connected = false;
            Serial.printf("[WS] Disconnected  total_conn=%u\n", conn_count);
            break;

        case WStype_TEXT:
            Serial.printf("[WS] RX: %.*s\n", (int)length, payload);
            handle_server_cmd(String((char*)payload, length));
            break;

        case WStype_ERROR:
            Serial.println("[WS] Error");
            break;

        default:
            break;
    }
}

// =============================================================================
// Server command handler
// =============================================================================

static void handle_server_cmd(const String& msg) {
    sensor_t* s = esp_camera_sensor_get();
    if (!s) return;

    // Trích int value từ JSON tối giản: {"cmd":..., "value": N}
    auto get_value = [&]() -> int {
        int idx = msg.indexOf("\"value\":");
        if (idx < 0) return -1;
        return msg.substring(idx + 8).toInt();
    };

    if (msg.indexOf("\"set_quality\"") >= 0) {
        int v = constrain(get_value(), 0, 63);
        s->set_quality(s, v);
        Serial.printf("[CMD] quality=%d\n", v);

    } else if (msg.indexOf("\"set_framesize\"") >= 0) {
        int v = get_value();
        if (v >= 0) { s->set_framesize(s, (framesize_t)v); Serial.printf("[CMD] framesize=%d\n", v); }

    } else if (msg.indexOf("\"set_vflip\"") >= 0) {
        int v = get_value();
        if (v >= 0) s->set_vflip(s, v);

    } else if (msg.indexOf("\"set_hmirror\"") >= 0) {
        int v = get_value();
        if (v >= 0) s->set_hmirror(s, v);

    } else if (msg.indexOf("\"ping\"") >= 0) {
        send_pong();

    } else if (msg.indexOf("\"restart\"") >= 0) {
        Serial.println("[CMD] Restart requested");
        delay(500);
        ESP.restart();
    }
}

// =============================================================================
// Helpers
// =============================================================================

static void send_pong() {
    char buf[192];
    snprintf(buf, sizeof(buf),
             "{\"type\":\"pong\",\"frames\":%u,\"fails\":%u,"
             "\"heap\":%u,\"block\":%u,\"rssi\":%d,\"conn\":%u}",
             frame_count, fb_fail_count,
             ESP.getFreeHeap(),
             (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_DEFAULT),
             WiFi.RSSI(), conn_count);
    ws.sendTXT(buf);
}

static void print_stats() {
    Serial.printf("[STATS] frames=%u  fails=%u  heap=%u  block=%u  rssi=%d\n",
                  frame_count, fb_fail_count,
                  ESP.getFreeHeap(),
                  (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_DEFAULT),
                  WiFi.RSSI());
}

// =============================================================================
// Camera
// =============================================================================

static bool init_camera() {
    const bool psram = psramFound();
    Serial.printf("[CAM] PSRAM: %s\n", psram ? "YES" : "NO");

    camera_config_t cfg = {};
    cfg.ledc_channel = LEDC_CHANNEL_0;
    cfg.ledc_timer   = LEDC_TIMER_0;
    cfg.pin_d0       = Y2_GPIO_NUM;
    cfg.pin_d1       = Y3_GPIO_NUM;
    cfg.pin_d2       = Y4_GPIO_NUM;
    cfg.pin_d3       = Y5_GPIO_NUM;
    cfg.pin_d4       = Y6_GPIO_NUM;
    cfg.pin_d5       = Y7_GPIO_NUM;
    cfg.pin_d6       = Y8_GPIO_NUM;
    cfg.pin_d7       = Y9_GPIO_NUM;
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

    // ── BUG FIX: fb_location & grab_mode phải nằm trong cùng nhánh PSRAM ──
    // ── BUG FIX: GRAB_LATEST + fb_count=2 gây deadlock buffer → dùng GRAB_WHEN_EMPTY ──
    if (psram) {
        cfg.frame_size   = FRAME_SIZE;
        cfg.jpeg_quality = JPEG_QUALITY_PSRAM;
        cfg.fb_count     = 2;
        cfg.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;
        cfg.fb_location  = CAMERA_FB_IN_PSRAM;
    } else {
        cfg.frame_size   = FRAME_SIZE;
        cfg.jpeg_quality = JPEG_QUALITY_DRAM;
        cfg.fb_count     = 1;
        cfg.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;
        cfg.fb_location  = CAMERA_FB_IN_DRAM;
    }

    esp_err_t err = esp_camera_init(&cfg);
    if (err != ESP_OK) {
        Serial.printf("[CAM] Init failed: 0x%x\n", err);
        return false;
    }

    sensor_t* s = esp_camera_sensor_get();
    if (!s) {
        Serial.println("[CAM] sensor_get() NULL");
        return false;
    }

    // OV2640 PID = 0x26 — nếu khác thì phần cứng có vấn đề
    Serial.printf("[CAM] Sensor PID: 0x%02x\n", s->id.PID);

    s->set_framesize(s,     FRAME_SIZE);
    s->set_quality(s,       psram ? JPEG_QUALITY_PSRAM : JPEG_QUALITY_DRAM);
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

    Serial.println("[CAM] Init OK");
    return true;
}

// Flush N frame đầu để AE/AWB lock, DMA ổn định
static void warmup_camera() {
    Serial.printf("[CAM] Warmup %u frames...\n", CAM_WARMUP_FRAMES);
    uint8_t ok = 0;
    for (uint8_t i = 0; i < CAM_WARMUP_FRAMES; i++) {
        camera_fb_t* fb = esp_camera_fb_get();
        if (fb) { ok++; esp_camera_fb_return(fb); }
        delay(CAM_WARMUP_DELAY_MS);
    }
    Serial.printf("[CAM] Warmup done  ok=%u/%u\n", ok, CAM_WARMUP_FRAMES);
}

// Reinit toàn bộ driver khi quá nhiều fail liên tiếp
static void reinit_camera() {
    Serial.println("[CAM] Reinit...");
    esp_camera_deinit();
    delay(500);
    if (!init_camera()) {
        Serial.println("[CAM] Reinit failed → restart");
        delay(1000);
        ESP.restart();
    }
    warmup_camera();
    fb_fail_count = 0;
}

// Lấy 1 frame, retry trong FB_GET_TIMEOUT_MS
static bool send_frame() {
    camera_fb_t*   fb       = nullptr;
    const uint32_t deadline = millis() + FB_GET_TIMEOUT_MS;

    while (!fb && millis() < deadline) {
        fb = esp_camera_fb_get();
        if (!fb) delay(10);
    }

    if (!fb) {
        fb_fail_count++;
        Serial.printf("[CAM] fb_get failed  total=%u  block=%u\n",
                      fb_fail_count,
                      (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_DEFAULT));

        if (fb_fail_count % CAM_FAIL_REINIT == 0) reinit_camera();
        return false;
    }

    bool ok = false;
    if (fb->format == PIXFORMAT_JPEG && fb->len > 0) {
        ok = ws.sendBIN(fb->buf, fb->len);
    } else {
        Serial.printf("[CAM] Bad frame fmt=%d len=%zu — skip\n",
                      (int)fb->format, fb->len);
        ok = true;  // không fatal
    }

    esp_camera_fb_return(fb);
    return ok;
}

// =============================================================================
// Wi-Fi
// =============================================================================

static bool connect_wifi() {
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);
    WiFi.setTxPower(WIFI_POWER_17dBm);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    Serial.printf("[WiFi] Connecting to \"%s\"", WIFI_SSID);
    const uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED) {
        delay(250);
        Serial.print('.');
        if (millis() - t0 > WIFI_TIMEOUT_MS) {
            Serial.println("\n[WiFi] Timeout");
            return false;
        }
    }
    Serial.printf("\n[WiFi] OK  IP=%s  RSSI=%d dBm\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
    return true;
}

// =============================================================================
// WebSocket setup
// =============================================================================

static void setup_websocket() {
    ws.begin(WS_HOST, WS_PORT, WS_PATH);
    ws.onEvent(onWebSocketEvent);
    ws.setReconnectInterval(WS_RECONNECT_MS);
    ws.enableHeartbeat(WS_HEARTBEAT_MS, WS_HEARTBEAT_TO_MS, WS_HEARTBEAT_RETRY);
    Serial.printf("[WS] Target: ws://%s:%d%s\n", WS_HOST, WS_PORT, WS_PATH);
}

// =============================================================================
// Arduino entry points
// =============================================================================

void setup() {
    Serial.begin(115200);
    delay(300);

    Serial.println("\n=== ESP32-CAM WebSocket Client ===");
    Serial.printf("Heap : %u B\n", ESP.getFreeHeap());
    Serial.printf("PSRAM: %u B\n", ESP.getFreePsram());

    if (!init_camera()) {
        Serial.println("[FATAL] Camera → restart");
        delay(2000);
        ESP.restart();
    }

    warmup_camera();   // Flush frame đầu TRƯỚC khi connect WiFi

    if (!connect_wifi()) {
        Serial.println("[FATAL] WiFi → restart");
        delay(2000);
        ESP.restart();
    }

    setup_websocket();
}

void loop() {
    ws.loop();

    if (!ws_connected) return;

    const uint32_t now = millis();
    if (now - last_frame_ms < FRAME_INTERVAL_MS) return;
    last_frame_ms = now;

    if (send_frame()) {
        frame_count++;
        if (frame_count % LOG_EVERY_N_FRAMES == 0) print_stats();
    }
}