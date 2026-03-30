#include <Arduino.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_http_server.h>

// -----------------------------
// Wi-Fi credentials
// -----------------------------
static const char* WIFI_SSID = "ITF Da Nang";
static const char* WIFI_PASS = "itfdanang";

// -----------------------------
// AI Thinker ESP32-CAM pins
// -----------------------------
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

static httpd_handle_t camera_httpd = nullptr;
static httpd_handle_t stream_httpd = nullptr;

static const framesize_t STREAM_FRAME_SIZE = FRAMESIZE_VGA;
static const int STREAM_JPEG_QUALITY = 10;

// ─── Index page ───────────────────────────────────────────────────────────────
static esp_err_t index_handler(httpd_req_t* req) {
    static const char page[] =
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>ESP32-CAM LAN</title>"
        "<style>"
        "body{margin:0;background:#10151b;color:#e7eef7;font-family:Verdana,sans-serif;}"
        ".wrap{max-width:960px;margin:16px auto;padding:0 12px;}"
        "h1{font-size:18px;margin:0 0 10px;}"
        "img{width:100%;border-radius:12px;border:1px solid #263241;background:#000;}"
        "button{margin-top:10px;padding:8px 12px;border:0;border-radius:8px;"
        "background:#2f81f7;color:#fff;cursor:pointer;}"
        "</style></head><body><div class='wrap'>"
        "<h1>ESP32-CAM LAN Stream</h1>"
        "<img id='stream' alt='stream'>"
        "<br><button onclick='window.open(\"/jpg\",\"_blank\")'>Capture JPG</button>"
        "</div><script>"
        "document.getElementById('stream').src='http://'+location.hostname+':81/stream';"
        "</script></body></html>";

    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, page, HTTPD_RESP_USE_STRLEN);
}

// ─── Single JPEG capture ──────────────────────────────────────────────────────
static esp_err_t jpg_handler(httpd_req_t* req) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) return httpd_resp_send_500(req);

    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store, no-cache, must-revalidate");
    esp_err_t res = httpd_resp_send(req, reinterpret_cast<const char*>(fb->buf), fb->len);
    esp_camera_fb_return(fb);
    return res;
}

// ─── Status JSON ──────────────────────────────────────────────────────────────
static esp_err_t status_handler(httpd_req_t* req) {
    char json[128];
    int n = snprintf(json, sizeof(json),
                     "{\"ip\":\"%s\",\"rssi\":%d,\"psram\":%u}",
                     WiFi.localIP().toString().c_str(),
                     WiFi.RSSI(),
                     ESP.getFreePsram());
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_send(req, json, n);
}

// ─── MJPEG stream ─────────────────────────────────────────────────────────────
static esp_err_t stream_handler(httpd_req_t* req) {
    static const char* CONTENT_TYPE  = "multipart/x-mixed-replace;boundary=frame";
    static const char* BOUNDARY      = "\r\n--frame\r\n";
    static const char* PART_HDR_FMT  = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

    httpd_resp_set_type(req, CONTENT_TYPE);
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    // ★ Disable Nagle — reduces latency on each chunk
    httpd_resp_set_hdr(req, "X-Framerate", "30");

    char part_buf[64];
    esp_err_t res = ESP_OK;

    while (true) {
        camera_fb_t* fb = esp_camera_fb_get();
        if (!fb) { res = ESP_FAIL; break; }

        int hdr_len = snprintf(part_buf, sizeof(part_buf), PART_HDR_FMT, fb->len);

        res = httpd_resp_send_chunk(req, BOUNDARY, strlen(BOUNDARY));
        if (res == ESP_OK)
            res = httpd_resp_send_chunk(req, part_buf, hdr_len);
        if (res == ESP_OK)
            res = httpd_resp_send_chunk(req, reinterpret_cast<const char*>(fb->buf), fb->len);
        if (res == ESP_OK)
            res = httpd_resp_send_chunk(req, "\r\n", 2);

        esp_camera_fb_return(fb);

        if (res != ESP_OK) break;

        // ★ Yield CPU so Wi-Fi stack & watchdog stay healthy
        taskYIELD();
    }
    return res;
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

    // 20 MHz is more stable on many ESP32-CAM + USB-TTL setups.
    cfg.xclk_freq_hz  = 20000000;
    cfg.pixel_format  = PIXFORMAT_JPEG;
    cfg.grab_mode     = CAMERA_GRAB_LATEST;   // luôn lấy frame mới nhất
    cfg.fb_location   = CAMERA_FB_IN_PSRAM;

    if (psramFound()) {
        cfg.frame_size   = STREAM_FRAME_SIZE;
        cfg.jpeg_quality = STREAM_JPEG_QUALITY;
        cfg.fb_count     = 2;
    } else {
        cfg.frame_size   = FRAMESIZE_QVGA;
        cfg.jpeg_quality = 14;
        cfg.fb_count     = 1;
        cfg.fb_location  = CAMERA_FB_IN_DRAM;
    }

    if (esp_camera_init(&cfg) != ESP_OK) {
        Serial.println("Camera init failed");
        return false;
    }

    // ─── Fine-tune sensor ─────────────────────────────────────────────────────
    sensor_t* s = esp_camera_sensor_get();
    if (s) {
        s->set_framesize(s,   psramFound() ? STREAM_FRAME_SIZE : FRAMESIZE_QVGA);
        s->set_quality(s,     psramFound() ? STREAM_JPEG_QUALITY : 14);
        s->set_brightness(s,  0);    // -2..2
        s->set_contrast(s,    1);    // -2..2
        s->set_saturation(s,  0);
        s->set_sharpness(s,   2);    // 0..2
        s->set_denoise(s,     1);    // bật khử nhiễu
        s->set_ae_level(s,    1);    // auto-exposure boost nhẹ
        s->set_awb_gain(s,    1);    // auto white-balance gain
        s->set_whitebal(s,    1);
        s->set_exposure_ctrl(s, 1);  // auto exposure ON
        s->set_gain_ctrl(s,   1);    // auto gain ON
        s->set_lenc(s,        1);    // lens correction
        s->set_hmirror(s,     0);
        s->set_vflip(s,       0);
    }
    return true;
}

// ─── Wi-Fi ────────────────────────────────────────────────────────────────────
static bool connect_wifi() {
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);      // tắt power-save, giảm jitter
    WiFi.setTxPower(WIFI_POWER_19_5dBm);  // ★ max TX power
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    Serial.print("Connecting to WiFi");
    const uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED) {
        delay(250);
        Serial.print('.');
        if (millis() - t0 > 20000) {
            Serial.println("\nWiFi timeout");
            return false;
        }
    }
    Serial.println("\nConnected");
    Serial.printf("IP: %s  RSSI: %d dBm\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
    return true;
}

// ─── HTTP servers ─────────────────────────────────────────────────────────────
static bool start_camera_server() {
    // --- Port 80: index / jpg / status ---
    httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
    cfg.server_port       = 80;
    cfg.max_uri_handlers  = 8;
    cfg.stack_size        = 8192;

    if (httpd_start(&camera_httpd, &cfg) != ESP_OK) return false;

    const httpd_uri_t uris[] = {
        { "/",       HTTP_GET, index_handler,  nullptr },
        { "/jpg",    HTTP_GET, jpg_handler,    nullptr },
        { "/status", HTTP_GET, status_handler, nullptr },
    };
    for (auto& u : uris) httpd_register_uri_handler(camera_httpd, &u);

    // --- Port 81: MJPEG stream ---
    httpd_config_t scfg = HTTPD_DEFAULT_CONFIG();
    scfg.server_port      = 81;
    scfg.ctrl_port        = cfg.ctrl_port + 1;
    scfg.max_uri_handlers = 4;
    scfg.stack_size       = 16384;
    scfg.recv_wait_timeout = 10;
    scfg.send_wait_timeout = 10;
    scfg.lru_purge_enable  = true;

    if (httpd_start(&stream_httpd, &scfg) != ESP_OK) return false;

    const httpd_uri_t stream_uri = {
        "/stream", HTTP_GET, stream_handler, nullptr
    };
    httpd_register_uri_handler(stream_httpd, &stream_uri);

    return true;
}

// ─── Arduino entry points ─────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n=== ESP32-CAM Boot ===");
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
    if (!start_camera_server()) {
        Serial.println("Server error — restarting");
        delay(2000); ESP.restart();
    }

    Serial.printf("\nReady!  http://%s\n",        WiFi.localIP().toString().c_str());
    Serial.printf("Stream: http://%s:81/stream\n", WiFi.localIP().toString().c_str());
}

void loop() {
    delay(1000);
}