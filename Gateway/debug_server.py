"""
debug_server.py – Standalone YOLO debug server for RoadSentinel DMS.

Runs two services:
  - HTTP  :9002  → MJPEG stream  (GET /stream)
  - WS    :9001  → Detection JSON (ws://localhost:9001)

Usage:
    cd /Users/anhnon/RoadSentinel/Gateway
    python debug_server.py
"""

import asyncio
import base64
import json
import logging
import sys
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import cv2
from ultralytics import YOLO

from app.capture.esp32 import ESP32Capture
from app.evidence.recorder import EvidenceRecorder
from app.evidence.trigger import SleepWindowTrigger
from app.utils.config import CONFIG, CaptureConfig, EvidenceConfig

try:
    import yaml
except ImportError:
    yaml = None

try:
    from websockets import serve as ws_serve
except ImportError:
    sys.exit("ERROR: websockets not installed. Run: pip install websockets>=12.0")

# ─── Config ──────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
CONFIG_FILE = ROOT_DIR / "config.yml"

_DEFAULT_CFG: dict[str, Any] = {
    "model_path": "models/best.pt",
    "esp32_stream_url": "http://192.168.1.157:81/stream",
    "inference_width": 640,
    "inference_height": 480,
    "confidence_threshold": 0.40,
    "iou_threshold": 0.45,
    "fps_limit": 10,
    "ws_port": 9001,
    "http_port": 9002,
    "violation_confidence_threshold": 0.60,
    "evidence_device_id": "debug_server",
    "evidence_window_seconds": 8,
    "evidence_trigger_ratio": 0.9,
}


def _load_debug_server_cfg() -> dict[str, Any]:
    cfg = dict(_DEFAULT_CFG)

    if not CONFIG_FILE.exists():
        print(f"[debug_server] config.yml not found at {CONFIG_FILE}, using defaults")
        return cfg

    if yaml is None:
        print(
            "[debug_server] pyyaml not installed, cannot read config.yml; using defaults"
        )
        return cfg

    try:
        raw = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        print(f"[debug_server] failed to parse config.yml ({exc}), using defaults")
        return cfg

    section = raw.get("debug_server") if isinstance(raw, dict) else None
    if isinstance(section, dict):
        cfg.update(section)
        # Accept gateway-style key for convenience.
        if "esp32_stream_url" not in section and "esp32_url" in section:
            cfg["esp32_stream_url"] = section["esp32_url"]
    elif isinstance(raw, dict):
        # Backward-compatible: allow top-level keys.
        cfg.update({k: v for k, v in raw.items() if k in cfg})

    return cfg


_CFG = _load_debug_server_cfg()

MODEL_PATH = ROOT_DIR / str(_CFG["model_path"])
ESP32_STREAM_URL = str(_CFG["esp32_stream_url"])
INFERENCE_W = int(_CFG["inference_width"])  # inference resolution width
INFERENCE_H = int(_CFG["inference_height"])  # inference resolution height
CONF_THRESH = float(_CFG["confidence_threshold"])
IOU_THRESH = float(_CFG["iou_threshold"])
FPS_LIMIT = int(_CFG["fps_limit"])  # max inference FPS (cap to not fry CPU)
WS_PORT = int(_CFG["ws_port"])
HTTP_PORT = int(_CFG["http_port"])
VIOLATION_CONF_THRESH = float(_CFG["violation_confidence_threshold"])
EVIDENCE_DEVICE_ID = str(_CFG["evidence_device_id"])
EVIDENCE_WINDOW_SECONDS = int(_CFG["evidence_window_seconds"])
EVIDENCE_TRIGGER_RATIO = float(_CFG["evidence_trigger_ratio"])

# ─── Logging ────────────────────────────────────────────────────────────────
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "debug_server.log"

_log_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_log_formatter)

_file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(_log_formatter)

logging.basicConfig(level=logging.DEBUG, handlers=[_console_handler, _file_handler])
log = logging.getLogger("debug_server")

# ─── Shared state (thread-safe via GIL for simple reads/writes) ──────────────
_lock = threading.Lock()
_latest_jpeg: bytes | None = None  # MJPEG frame bytes
_latest_payload: dict | None = None  # Detection JSON payload

# ─── Event logic ─────────────────────────────────────────

# Warning thresholds in seconds
_EVENT_THRESH_SEC = {
    "sleeping": 1.5,
    "using_phone": 1.0,
    "distracted": 2.0,
    "drinking": 1.5,
}

_EVENT_MAPPING = {
    "eyes closed": "sleeping",
    "yawning": "sleeping",
    "mobile": "using_phone",
    "texting": "using_phone",
    "driver talking on phone": "using_phone",
    "driver looking away": "distracted",
    "driver reaching behind": "distracted",
    "drinking": "drinking",
}

_event_counters = {k: 0 for k in _EVENT_THRESH_SEC.keys()}


def classify_event(detections: list[dict]) -> tuple[str, float, int]:
    global _event_counters

    # 1. Filter high confidence bbox
    valid_dets = [d for d in detections if d["confidence"] >= VIOLATION_CONF_THRESH]
    labels_present = {d["label"].lower(): d["confidence"] for d in valid_dets}

    current_events = set()
    event_confs = {}

    for label, conf in labels_present.items():
        if label in _EVENT_MAPPING:
            ev = _EVENT_MAPPING[label]
            current_events.add(ev)
            event_confs[ev] = max(event_confs.get(ev, 0.0), conf)

    triggered_event = "normal"
    highest_conf = 0.0
    max_ctr = 0

    # 2. Update states
    for ev, thresh_sec in _EVENT_THRESH_SEC.items():
        frames_needed = int(thresh_sec * FPS_LIMIT)

        if ev in current_events:
            _event_counters[ev] += 1
        else:
            # Cool down to avoid flickering
            _event_counters[ev] = max(0, _event_counters[ev] - 1)

        if _event_counters[ev] >= frames_needed:
            triggered_event = ev
            highest_conf = event_confs.get(ev, 1.0)

        max_ctr = max(max_ctr, _event_counters[ev])

    if triggered_event == "normal":
        if valid_dets:
            highest_conf = max(d["confidence"] for d in valid_dets)

    return triggered_event, highest_conf, max_ctr


# ─── Capture + inference thread ─────────────────────────────────────────────
def inference_loop():
    global _latest_jpeg, _latest_payload

    log.info("Loading YOLO model: %s", MODEL_PATH)
    if not MODEL_PATH.exists():
        log.error("Model not found at %s", MODEL_PATH)
        sys.exit(1)

    model = YOLO(str(MODEL_PATH))
    log.info("Model loaded. Class names: %s", list(model.names.values()))

    capture_cfg = CaptureConfig(
        source="esp32",
        webcam_index=0,
        esp32_url=ESP32_STREAM_URL,
        target_fps=FPS_LIMIT,
    )
    cap = ESP32Capture(capture_cfg)
    cap.start()
    log.info(
        "ESP32 capture started (%s) target=%dfps infer=%dx%d",
        ESP32_STREAM_URL,
        FPS_LIMIT,
        INFERENCE_W,
        INFERENCE_H,
    )

    frame_id = 0
    fps_history: list[float] = []
    min_dt = 1.0 / FPS_LIMIT
    t_last = time.monotonic()

    evidence_cfg = EvidenceConfig(
        sleep_evidence_seconds=EVIDENCE_WINDOW_SECONDS,
        sleep_trigger_ratio=EVIDENCE_TRIGGER_RATIO,
    )
    evidence_recorder = EvidenceRecorder(
        evidence_cfg,
        fps=FPS_LIMIT,
        device_id=EVIDENCE_DEVICE_ID,
        cloudinary_cfg=CONFIG.cloudinary,
    )
    evidence_trigger = SleepWindowTrigger(
        fps=FPS_LIMIT,
        window_seconds=evidence_cfg.sleep_evidence_seconds,
        occupancy_threshold=evidence_cfg.sleep_trigger_ratio,
    )
    log.info(
        "Evidence enabled=%s window=%ss ratio=%.2f cloudinary=%s",
        evidence_cfg.enabled,
        evidence_cfg.sleep_evidence_seconds,
        evidence_cfg.sleep_trigger_ratio,
        CONFIG.cloudinary.enabled,
    )

    while True:
        frame = cap.read(timeout=2.0)
        if frame is None:
            log.warning("No frame from ESP32 stream – waiting for next frame…")
            time.sleep(0.1)
            continue

        if frame.shape[1] != INFERENCE_W or frame.shape[0] != INFERENCE_H:
            frame = cv2.resize(
                frame, (INFERENCE_W, INFERENCE_H), interpolation=cv2.INTER_AREA
            )

        now = time.monotonic()
        elapsed = now - t_last
        if elapsed < min_dt:
            time.sleep(min_dt - elapsed)
            continue
        t_last = time.monotonic()

        fps_inst = 1.0 / max(elapsed, 1e-6)
        fps_history.append(fps_inst)
        if len(fps_history) > 30:
            fps_history.pop(0)
        fps_avg = sum(fps_history) / len(fps_history)

        h, w = frame.shape[:2]

        # ── YOLO inference ──────────────────────────────────────────────────
        results = model.predict(
            source=frame,
            conf=CONF_THRESH,
            iou=IOU_THRESH,
            verbose=False,
        )

        detections: list[dict] = []
        annotated = frame.copy()

        for result in results:
            if result.boxes is None:
                continue
            names: dict[int, str] = result.names
            for box in result.boxes:
                cid = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                label = names.get(cid, str(cid))
                detections.append(
                    {
                        "label": label,
                        "class_id": cid,
                        "confidence": round(conf, 3),
                        "bbox": [
                            round(x1, 1),
                            round(y1, 1),
                            round(x2, 1),
                            round(y2, 1),
                        ],
                    }
                )

        event, event_conf, current_ctr = classify_event(detections)

        # ── Annotate frame for MJPEG preview ───────────────────────────────
        COLOR_MAP = {
            "Driver": (59, 130, 246),
            "Eyes Open": (16, 185, 129),
            "Eyes Closed": (239, 68, 68),
            "Seat Belt": (139, 92, 246),
            "Drinking": (245, 158, 11),
            "Driver talking on phone": (236, 72, 153),
            "Driver Looking away": (249, 115, 22),
            "Mobile": (168, 85, 247),
            "Yawning": (6, 182, 212),
            "Texting": (99, 102, 241),
            "Driver Reaching behind": (132, 204, 22),
        }
        DEFAULT_COLOR = (148, 163, 184)

        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
            color = COLOR_MAP.get(det["label"], DEFAULT_COLOR)
            # BGR for OpenCV
            bgr = (color[2], color[1], color[0])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), bgr, 2)
            txt = f"{det['label']} {det['confidence']:.0%}"
            (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            ty = y1 - 6 if y1 > 20 else y2 + th + 6
            cv2.rectangle(annotated, (x1, ty - th - 4), (x1 + tw + 4, ty + 2), bgr, -1)
            cv2.putText(
                annotated,
                txt,
                (x1 + 2, ty),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )

        # Event overlay
        event_colors = {
            "normal": (16, 185, 129),
            "sleeping": (239, 68, 68),
            "distracted": (245, 158, 11),
            "using_phone": (139, 92, 246),
        }
        ec = event_colors.get(event, DEFAULT_COLOR)
        ec_bgr = (ec[2], ec[1], ec[0])
        overlay_txt = f"EVENT: {event.upper()}  ctr={current_ctr}"
        cv2.rectangle(annotated, (0, 0), (len(overlay_txt) * 8 + 16, 28), (0, 0, 0), -1)
        cv2.putText(
            annotated, overlay_txt, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, ec_bgr, 1
        )
        fps_txt = f"FPS:{fps_avg:.1f}  #{frame_id}"
        cv2.putText(
            annotated,
            fps_txt,
            (w - 130, 19),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 200),
            1,
        )

        evidence_recorder.push_frame(annotated)
        if evidence_trigger.update(event == "sleeping"):
            saved = evidence_recorder.save_sleeping_clip(event_conf)
            if saved is not None:
                log.warning("Evidence written to %s", saved)

        # ── Encode JPEG & build payload ─────────────────────────────────
        _, jpeg_buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        jpeg_bytes = jpeg_buf.tobytes()
        frame_b64 = base64.b64encode(jpeg_bytes).decode("ascii")

        payload = {
            "frame_id": frame_id,
            "fps": round(fps_avg, 1),
            "frame_w": w,
            "frame_h": h,
            "event": event,
            "event_conf": round(event_conf, 3),
            "sleep_ctr": current_ctr,  # kept name for UI backward compat
            "detections": detections,
            "frame_b64": frame_b64,
        }

        with _lock:
            _latest_jpeg = jpeg_bytes
            _latest_payload = payload

        frame_id += 1
        if frame_id % FPS_LIMIT == 0:
            log.info(
                "frame=%d  fps=%.1f  event=%s  dets=%d",
                frame_id,
                fps_avg,
                event,
                len(detections),
            )


# ─── MJPEG HTTP server ───────────────────────────────────────────────────────
class MJPEGHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # type: ignore
        pass  # suppress access log

    def do_GET(self):
        if self.path == "/stream":
            self.send_response(200)
            self.send_header(
                "Content-Type", "multipart/x-mixed-replace; boundary=frame"
            )
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                while True:
                    with _lock:
                        frame = _latest_jpeg
                    if frame:
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n")
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                    time.sleep(0.05)
            except (BrokenPipeError, ConnectionResetError):
                pass
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()


def start_http_server():
    server = HTTPServer(("0.0.0.0", HTTP_PORT), MJPEGHandler)
    log.info("MJPEG stream → http://localhost:%d/stream", HTTP_PORT)
    server.serve_forever()


# ─── WebSocket server ────────────────────────────────────────────────────────
_ws_clients: set = set()


async def ws_handler(websocket):
    global _ws_clients
    _ws_clients.add(websocket)
    client = websocket.remote_address
    log.info("WS client connected: %s", client)
    try:
        async for _ in websocket:
            pass  # ignore incoming messages
    except Exception:
        pass
    finally:
        _ws_clients.discard(websocket)
        log.info("WS client disconnected: %s", client)


async def ws_broadcast_loop():
    """Push latest detection payload to all WS clients at ~FPS_LIMIT Hz."""
    global _ws_clients, _latest_payload
    interval = 1.0 / FPS_LIMIT
    while True:
        await asyncio.sleep(interval)
        if not _ws_clients:
            continue
        with _lock:
            payload = _latest_payload
        if payload is None:
            continue
        msg = json.dumps(payload)
        dead = set()
        for ws in list(_ws_clients):
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        _ws_clients -= dead


async def async_main():
    log.info("WebSocket server → ws://localhost:%d", WS_PORT)
    async with ws_serve(
        ws_handler,
        "0.0.0.0",
        WS_PORT,
        ping_interval=20,
        ping_timeout=10,
    ):
        await ws_broadcast_loop()


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("=" * 55)
    log.info("  RoadSentinel YOLO Debug Server")
    log.info("  Model : %s", MODEL_PATH)
    log.info("  Input : %s", ESP32_STREAM_URL)
    log.info("  HTTP  : http://localhost:%d/stream  (MJPEG)", HTTP_PORT)
    log.info("  WS    : ws://localhost:%d            (JSON detections)", WS_PORT)
    log.info("=" * 55)

    # Inference thread
    t = threading.Thread(target=inference_loop, daemon=True, name="inference")
    t.start()

    # MJPEG HTTP thread
    t2 = threading.Thread(target=start_http_server, daemon=True, name="mjpeg")
    t2.start()

    # WebSocket async loop (main thread)
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        log.info("Shutdown requested → bye!")
