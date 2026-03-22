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

