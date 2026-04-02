gateway/
│
├── app/
│   ├── main.py              # entry point (chạy chương trình)
│   │
│   ├── capture/
│   │   ├── webcam.py       # lấy frame từ webcam
│   │   ├── esp32.py        # lấy stream từ ESP32
│   │
│   ├── inference/
│   │   ├── model.py        # load YOLOv8
│   │   ├── detect.py       # chạy inference
│   │
│   ├── processing/
│   │   ├── preprocess.py   # resize, normalize
│   │   ├── postprocess.py  # xử lý output YOLO
│   │
│   ├── event/
│   │   ├── logic.py        # suy luận hành vi (sleep, phone)
│   │
│   ├── sender/
│   │   ├── websocket.py    # gửi data qua WebSocket
│   │   ├── http.py         # gửi HTTP fallback
│   │
│   ├── utils/
│   │   ├── config.py       # config (URL server, FPS…)
│   │   ├── logger.py       # logging
│
├── models/
│   └── best.pt             # model YOLOv8
│
├── tests/
│   ├── test_event_logic.py      # test phân loại event
│   └── test_config_validation.py # test validation config
│
├── docs/
│   └── production-readiness-checklist.md
│
├── requirements.txt
└── README.md

Run tests:

pytest -q

Production checklist:

docs/production-readiness-checklist.md

---

## ESP32-CAM simulator (webcam -> LAN)

Repo now includes `esp32_cam_simulator.py` to simulate ESP32-CAM MJPEG stream using your local webcam.

### 1) Start simulator (bind LAN)

```bash
cd /Users/anhnon/RoadSentinel/Gateway
python esp32_cam_simulator.py --host 0.0.0.0 --port 8081 --webcam-index 0
```

Available endpoints:

- `http://<LAN_IP>:8081/stream`
- `http://<LAN_IP>:8081/health`

Find your LAN IP on macOS:

```bash
ipconfig getifaddr en0
```

If you are on Ethernet, try:

```bash
ipconfig getifaddr en1
```

### 2) Point Gateway to simulator stream

Update `config.yml` under `gateway.capture`:

```yml
gateway:
	capture:
		source: esp32
		esp32_url: http://<LAN_IP>:8081/stream
		target_fps: 5
```

Gateway now supports capture overrides from:

- `config.yml` -> `gateway.capture`
- Environment variables:
	- `GATEWAY_CAPTURE_SOURCE`
	- `GATEWAY_ESP32_URL`
	- `GATEWAY_WEBCAM_INDEX`
	- `GATEWAY_TARGET_FPS`

### 3) Run gateway

```bash
python -m app.main
```

### Quick override without editing YAML

```bash
GATEWAY_CAPTURE_SOURCE=esp32 \
GATEWAY_ESP32_URL=http://<LAN_IP>:8081/stream \
python -m app.main
```
