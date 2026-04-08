import asyncio
import base64
from collections import deque
import importlib.util
import json
import logging
import pathlib
import time
from typing import Optional
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from application.alert.commands.create_alert import CreateAlertCommand
from application.alert.commands.create_alert_handler import CreateAlertHandler
from domain.alert.value_objects import AlertType
from infrastructure.db.session import SessionLocal
from infrastructure.repositories.alert_repository_impl import AlertRepositoryImpl
from shared.config import settings

logger = logging.getLogger("roadsentinel.ws")

# ─── AI model (optional — graceful fallback if not installed) ─────────────────

MODEL_PATH  = pathlib.Path(__file__).parents[4] / "AI" / "model" / "best.pt"
BACKEND_ROOT = pathlib.Path(__file__).parents[3]
EVIDENCE_DIR = BACKEND_ROOT / "evidence"
CONF_THRESH = 0.4
SKIP_FRAMES = 2          # run inference every N frames
INFER_W     = 320
INFER_H     = 240

if (
    importlib.util.find_spec("cv2") is not None
    and importlib.util.find_spec("numpy") is not None
    and importlib.util.find_spec("ultralytics") is not None
):
    _AI_AVAILABLE = True
else:
    _AI_AVAILABLE = False
    logger.warning("[AI] ultralytics/opencv not installed — detection disabled")

_yolo_model: Optional[object] = None

RELEVANT_CLASSES = {
    "cell phone",
    "mobile",
    "texting",
    "driver talking on phone",
    "person",
    "driver",
    "face",
    "eye",
    "eyes open",
    "sleeping",
    "eyes closed",
    "yawning",
    "drowsy",
    "distracted",
    "driver looking away",
    "driver reaching behind",
}

ALERT_EVENTS = {"sleeping", "using_phone", "distracted", "drowsy"}


class EventLogic:
    """Stateful event classifier with per-event hysteresis."""

    def __init__(self) -> None:
        self._no_presence_counter = 0

        self._event_scores: dict[str, int] = {
            "sleeping": 0,
            "using_phone": 0,
            "distracted": 0,
            "drowsy": 0,
        }
        self._event_miss_streaks: dict[str, int] = {
            "sleeping": 0,
            "using_phone": 0,
            "distracted": 0,
            "drowsy": 0,
        }
        self._event_active: dict[str, bool] = {
            "sleeping": False,
            "using_phone": False,
            "distracted": False,
            "drowsy": False,
        }

        self._decay_miss_frames = {
            "sleeping": 2,
            "using_phone": settings.DRIVER_EVENT_PHONE_DECAY_MISS_FRAMES,
            "distracted": 1,
            "drowsy": settings.DRIVER_EVENT_DROWSY_DECAY_MISS_FRAMES,
        }

        self._enter_thresholds = {
            "sleeping": settings.DRIVER_EVENT_SLEEP_ENTER_FRAMES,
            "using_phone": settings.DRIVER_EVENT_PHONE_ENTER_FRAMES,
            "distracted": settings.DRIVER_EVENT_DISTRACTED_ENTER_FRAMES,
            "drowsy": settings.DRIVER_EVENT_DROWSY_ENTER_FRAMES,
        }
        self._exit_thresholds = {
            "sleeping": settings.DRIVER_EVENT_SLEEP_EXIT_FRAMES,
            "using_phone": settings.DRIVER_EVENT_PHONE_EXIT_FRAMES,
            "distracted": settings.DRIVER_EVENT_DISTRACTED_EXIT_FRAMES,
            "drowsy": settings.DRIVER_EVENT_DROWSY_EXIT_FRAMES,
        }

        self._label_sets = {
            "sleeping": {"sleeping", "eyes closed"},
            "using_phone": {
                "cell phone",
                "mobile",
                "texting",
                "driver talking on phone",
            },
            "distracted": {
                "distracted",
                "driver looking away",
                "driver reaching behind",
            },
            "drowsy": {"yawning", "drowsy"},
        }

        self._confidence_thresholds = {
            "sleeping": settings.DRIVER_EVENT_MIN_SLEEP_CONFIDENCE,
            "using_phone": settings.DRIVER_EVENT_MIN_PHONE_CONFIDENCE,
            "distracted": settings.DRIVER_EVENT_MIN_DISTRACTED_CONFIDENCE,
            "drowsy": settings.DRIVER_EVENT_MIN_DROWSY_CONFIDENCE,
        }

        self._presence_labels = {
            label.strip().lower() for label in settings.DRIVER_EVENT_PRESENCE_LABELS
        }
        self._event_priority = tuple(
            event.strip().lower() for event in settings.DRIVER_EVENT_PRIORITY
        )
        self._unknown_enter_frames = settings.DRIVER_EVENT_UNKNOWN_ENTER_FRAMES

    @staticmethod
    def _max_conf_by_label(detections: list[dict]) -> dict[str, float]:
        out: dict[str, float] = {}
        for det in detections:
            label = str(det.get("label", "")).lower()
            conf = float(det.get("conf", det.get("confidence", 0.0)))
            prev = out.get(label, 0.0)
            if conf > prev:
                out[label] = conf
        return out

    def _update_event_state(self, event: str, has_evidence: bool) -> None:
        score = self._event_scores[event]
        enter = self._enter_thresholds[event]
        exit_ = self._exit_thresholds[event]

        if has_evidence:
            score = min(enter, score + 1)
            self._event_miss_streaks[event] = 0
        else:
            miss_streak = self._event_miss_streaks[event] + 1
            self._event_miss_streaks[event] = miss_streak
            if miss_streak >= self._decay_miss_frames[event]:
                score = max(0, score - 1)
                self._event_miss_streaks[event] = 0

        active = self._event_active[event]
        if active and score < exit_:
            active = False
        elif (not active) and score >= enter:
            active = True

        self._event_scores[event] = score
        self._event_active[event] = active

    def classify(self, detections: list[dict]) -> tuple[str, float]:
        label_conf = self._max_conf_by_label(detections)

        explicit_sleeping_conf = max(
            label_conf.get("sleeping", 0.0),
            label_conf.get("eyes closed", 0.0),
        )
        has_explicit_sleeping = (
            explicit_sleeping_conf >= self._confidence_thresholds["sleeping"]
        )

        has_presence = any(label in self._presence_labels for label in label_conf)
        if has_presence:
            self._no_presence_counter = 0
        else:
            self._no_presence_counter += 1

        event_confidence: dict[str, float] = {}
        for event in self._event_scores:
            evidence_conf = max(
                (
                    conf
                    for label, conf in label_conf.items()
                    if label in self._label_sets[event]
                ),
                default=0.0,
            )
            event_confidence[event] = evidence_conf
            has_evidence = evidence_conf >= self._confidence_thresholds[event]
            self._update_event_state(event, has_evidence)

        if has_explicit_sleeping:
            self._event_scores["sleeping"] = self._enter_thresholds["sleeping"]
            self._event_miss_streaks["sleeping"] = 0
            self._event_active["sleeping"] = True
            return "sleeping", explicit_sleeping_conf

        for event in self._event_priority:
            if self._event_active.get(event, False):
                return event, event_confidence.get(event, 0.0)

        if self._event_active.get("drowsy", False):
            return "drowsy", event_confidence.get("drowsy", 0.0)

        if self._no_presence_counter >= self._unknown_enter_frames:
            return "unknown", 0.0

        return "normal", 0.0

    def reset(self) -> None:
        self._no_presence_counter = 0
        for event in self._event_scores:
            self._event_scores[event] = 0
            self._event_miss_streaks[event] = 0
            self._event_active[event] = False


def _filter_detections(detections: list[dict]) -> list[dict]:
    filtered: list[dict] = [
        det for det in detections if str(det.get("label", "")).lower() in RELEVANT_CLASSES
    ]
    filtered.sort(key=lambda det: float(det.get("conf", det.get("confidence", 0.0))), reverse=True)
    return filtered


def _annotate_evidence_jpeg(
    jpeg_bytes: bytes,
    detections: list[dict],
    event: str,
    duration_ms: int,
    confidence: float,
) -> bytes:
    """Draw detections + event timing overlay for evidence clips."""
    if importlib.util.find_spec("cv2") is None or importlib.util.find_spec("numpy") is None:
        return jpeg_bytes

    try:
        import cv2 as _cv2  # type: ignore
        import numpy as _np  # type: ignore

        frame = _cv2.imdecode(_np.frombuffer(jpeg_bytes, dtype=_np.uint8), _cv2.IMREAD_COLOR)
        if frame is None:
            return jpeg_bytes

        for det in detections:
            bbox = det.get("bbox")
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue

            x1, y1, x2, y2 = [int(v) for v in bbox]
            conf = float(det.get("conf", det.get("confidence", 0.0)))
            label_name = str(det.get("label", "unknown"))
            label = f"{label_name} {conf:.0%}"

            _cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 136), 2)
            (tw, th), baseline = _cv2.getTextSize(label, _cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            top = max(0, y1 - th - baseline - 6)
            _cv2.rectangle(frame, (x1, top), (x1 + tw + 8, top + th + baseline + 4), (0, 255, 136), -1)
            _cv2.putText(
                frame,
                label,
                (x1 + 4, top + th + 1),
                _cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 0),
                1,
                _cv2.LINE_AA,
            )

        seconds = max(0, duration_ms // 1000)
        mm = seconds // 60
        ss = seconds % 60
        event_label = f"{event.upper()}  {mm:02d}:{ss:02d}  conf={confidence:.2f}"
        (tw, th), baseline = _cv2.getTextSize(event_label, _cv2.FONT_HERSHEY_SIMPLEX, 0.62, 2)
        _cv2.rectangle(frame, (10, 10), (10 + tw + 14, 10 + th + baseline + 12), (220, 38, 38), -1)
        _cv2.putText(
            frame,
            event_label,
            (17, 10 + th + 2),
            _cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            (255, 255, 255),
            2,
            _cv2.LINE_AA,
        )

        ok, encoded = _cv2.imencode(".jpg", frame, [_cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            return jpeg_bytes
        return encoded.tobytes()
    except Exception:
        return jpeg_bytes


class SleepWindowTrigger:
    """Triggers once when sleeping occupancy in a fixed window crosses threshold."""

    def __init__(self, fps: int, window_seconds: int, occupancy_threshold: float) -> None:
        self._window_frames = max(1, int(fps) * int(window_seconds))
        self._occupancy_threshold = occupancy_threshold
        self._window: deque[bool] = deque(maxlen=self._window_frames)
        self._latched = False

    def update(self, is_sleeping: bool) -> bool:
        self._window.append(is_sleeping)

        if len(self._window) < self._window_frames:
            return False

        sleeping_frames = sum(1 for state in self._window if state)
        occupancy = sleeping_frames / len(self._window)

        if sleeping_frames == 0:
            self._latched = False

        if occupancy >= self._occupancy_threshold and not self._latched:
            self._latched = True
            return True

        return False


class DriverEvidencePipeline:
    """Stores event frames, uploads clip to Cloudinary, then writes alert into DB."""

    def __init__(self, *, event_key: str, alert_type: AlertType) -> None:
        self._event_key = event_key
        self._alert_type = alert_type
        self._enabled = settings.DRIVER_EVENT_EVIDENCE_ENABLED
        self._fps = max(1, settings.DRIVER_EVENT_EVIDENCE_FPS)
        self._window_seconds = max(1, settings.DRIVER_EVENT_EVIDENCE_SECONDS)
        self._codec = settings.DRIVER_EVENT_EVIDENCE_CODEC
        self._buffer: deque[bytes] = deque(maxlen=self._fps * self._window_seconds)
        self._cloudinary_ready = False
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        self._configure_cloudinary()

    def _configure_cloudinary(self) -> None:
        if not settings.DRIVER_EVENT_CLOUDINARY_ENABLED:
            return
        if importlib.util.find_spec("cloudinary") is None:
            logger.warning("Cloudinary SDK not installed; evidence upload disabled")
            return

        try:
            import cloudinary  # type: ignore

            cloudinary.config(
                cloud_name=settings.DRIVER_EVENT_CLOUDINARY_CLOUD_NAME,
                api_key=settings.DRIVER_EVENT_CLOUDINARY_API_KEY,
                api_secret=settings.DRIVER_EVENT_CLOUDINARY_API_SECRET,
                secure=True,
            )
            self._cloudinary_ready = True
        except Exception as exc:
            logger.error("Failed to configure Cloudinary: %s", exc)

    def push_frame(self, jpeg_bytes: bytes) -> None:
        if not self._enabled:
            return
        self._buffer.append(jpeg_bytes)

    def reset_buffer(self) -> None:
        self._buffer.clear()

    @staticmethod
    def _alert_data(alert) -> dict:
        return {
            "_id": str(alert._id) if alert._id else None,
            "message": alert.message,
            "alert_type": alert.alert_type.value,
            "device_id": str(alert.device_id),
            "driver_id": str(alert.driver_id) if alert.driver_id else None,
            "vehicle_id": str(alert.vehicle_id) if alert.vehicle_id else None,
            "evidence_url": alert.evidence_url,
            "latitude": alert.latitude,
            "longitude": alert.longitude,
            "user": None,
            "vehicle": None,
            "_created_at": alert._created_at.isoformat() if alert._created_at else None,
            "_updated_at": alert._updated_at.isoformat() if alert._updated_at else None,
            "_deleted_at": alert._deleted_at.isoformat() if alert._deleted_at else None,
        }

    def _encode_clip(self, frames: list[bytes]) -> pathlib.Path | None:
        if not frames:
            return None

        import cv2 as _cv2  # type: ignore
        import numpy as _np  # type: ignore

        first = _cv2.imdecode(_np.frombuffer(frames[0], dtype=_np.uint8), _cv2.IMREAD_COLOR)
        if first is None:
            return None

        h, w = first.shape[:2]
        clip_name = f"{self._event_key}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.mp4"
        clip_path = EVIDENCE_DIR / clip_name

        writer = _cv2.VideoWriter(
            str(clip_path),
            _cv2.VideoWriter_fourcc(*self._codec),
            float(self._fps),
            (w, h),
        )
        if not writer.isOpened():
            clip_path.unlink(missing_ok=True)
            return None

        try:
            for jpeg in frames:
                frame = _cv2.imdecode(
                    _np.frombuffer(jpeg, dtype=_np.uint8),
                    _cv2.IMREAD_COLOR,
                )
                if frame is None:
                    continue
                if frame.shape[1] != w or frame.shape[0] != h:
                    frame = _cv2.resize(frame, (w, h), interpolation=_cv2.INTER_LINEAR)
                writer.write(frame)
        finally:
            writer.release()

        return clip_path

    def _upload_cloudinary(self, clip_path: pathlib.Path, confidence: float) -> str | None:
        if not self._cloudinary_ready:
            return None

        try:
            import cloudinary.uploader  # type: ignore

            public_id = f"{self._event_key}/{time.strftime('%Y-%m-%d')}/{uuid.uuid4()}"
            upload_result = cloudinary.uploader.upload(  # type: ignore
                str(clip_path),
                resource_type="video",
                public_id=public_id,
                folder=settings.DRIVER_EVENT_CLOUDINARY_FOLDER,
                overwrite=False,
                format="mp4",
                context={
                    "event": self._event_key,
                    "confidence": f"{confidence:.4f}",
                },
            )
            if isinstance(upload_result, dict):
                return upload_result.get("secure_url")
        except Exception as exc:
            logger.error("Cloudinary upload failed: %s", exc)
        return None

    def save_event_alert(self, confidence: float) -> dict | None:
        if not self._enabled:
            return None

        frames = list(self._buffer)
        if not frames:
            return None

        clip_path = self._encode_clip(frames)
        evidence_url: str | None = None
        if clip_path is not None:
            local_url = f"{settings.APP_PUBLIC_BASE_URL}/evidence/{clip_path.name}"
            evidence_url = self._upload_cloudinary(clip_path, confidence) or local_url

        message_by_event = {
            "sleeping": "Sleeping detected",
            "using_phone": "Phone usage detected",
        }
        alert_message = f"{message_by_event.get(self._event_key, 'Driver event detected')} (confidence={confidence:.2f})"

        db = SessionLocal()
        try:
            repository = AlertRepositoryImpl(db)
            handler = CreateAlertHandler(repository)
            alert = handler.handle(
                CreateAlertCommand(
                    message=alert_message,
                    alert_type=self._alert_type,
                    device_id=settings.DRIVER_EVENT_ALERT_DEVICE_ID,
                    driver_id=settings.DRIVER_EVENT_ALERT_DRIVER_ID,
                    vehicle_id=settings.DRIVER_EVENT_ALERT_VEHICLE_ID,
                    evidence_url=evidence_url,
                    latitude=None,
                    longitude=None,
                )
            )
            return self._alert_data(alert)
        except Exception as exc:
            logger.error("Failed to create %s alert in DB: %s", self._event_key, exc)
            return None
        finally:
            db.close()


def _load_model() -> None:
    global _yolo_model
    if not _AI_AVAILABLE:
        return
    if not MODEL_PATH.exists():
        logger.warning("[AI] model not found at %s — detection disabled", MODEL_PATH)
        return
    from ultralytics import YOLO as _YOLO  # type: ignore  # noqa: F401
    import numpy as _np                    # type: ignore  # noqa: F401
    _yolo_model = _YOLO(str(MODEL_PATH))
    # Warm-up — avoids latency spike on first real frame
    dummy = _np.zeros((INFER_H, INFER_W, 3), dtype=_np.uint8)
    _yolo_model(dummy, verbose=False)      # type: ignore
    logger.info("[AI] YOLO model loaded from %s", MODEL_PATH)



def run_inference(jpeg_bytes: bytes) -> list[dict]:
    """Decode JPEG, run YOLO, return list of {label, conf, bbox:[x1,y1,x2,y2]}."""
    if not _AI_AVAILABLE or _yolo_model is None:
        return []
    import cv2 as _cv2          # type: ignore
    import numpy as _np         # type: ignore
    arr   = _np.frombuffer(jpeg_bytes, dtype=_np.uint8)
    frame = _cv2.imdecode(arr, _cv2.IMREAD_COLOR)
    if frame is None:
        return []
    h, w = frame.shape[:2]
    small = _cv2.resize(frame, (INFER_W, INFER_H), interpolation=_cv2.INTER_LINEAR)
    sx, sy = w / float(INFER_W), h / float(INFER_H)
    results = _yolo_model(small, conf=CONF_THRESH, verbose=False)[0]  # type: ignore
    out: list[dict] = []
    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        out.append({
            "label": _yolo_model.names[int(box.cls[0])],       # type: ignore
            "conf":  round(float(box.conf[0]), 3),
            "bbox":  [int(x1*sx), int(y1*sy), int(x2*sx), int(y2*sy)],
        })
    return out



# ─── Alerts manager (existing) ────────────────────────────────────────────────

class AlertsWebSocketManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


# ─── Camera manager (ESP32-CAM) ───────────────────────────────────────────────

class CameraManager:
    """Holds the single ESP32-CAM WebSocket connection."""

    def __init__(self) -> None:
        self.ws: Optional[WebSocket] = None
        self.device_id: str = "esp32-cam"

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.ws = ws
        logger.info("ESP32-CAM connected")

    def disconnect(self) -> None:
        self.ws = None
        logger.info("ESP32-CAM disconnected")

    @property
    def is_online(self) -> bool:
        return self.ws is not None

    async def send_command(self, payload: dict) -> bool:
        """Forward a JSON command to the ESP32. Returns True on success."""
        if self.ws is None:
            return False
        try:
            await self.ws.send_text(json.dumps(payload))
            return True
        except Exception:
            self.disconnect()
            return False


# ─── Frontend manager (browser viewers) ──────────────────────────────────────

class FrontendManager:
    """Holds all browser WebSocket connections."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("Browser viewer connected. Total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("Browser viewer disconnected. Total: %d", len(self._connections))

    @property
    def has_clients(self) -> bool:
        return len(self._connections) > 0

    @property
    def client_count(self) -> int:
        return len(self._connections)

    async def broadcast(self, message: str) -> None:
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


# ─── Singletons ───────────────────────────────────────────────────────────────

alerts_ws_manager = AlertsWebSocketManager()
camera_mgr = CameraManager()
frontend_mgr = FrontendManager()

router = APIRouter(prefix="/ws", tags=["websocket"])


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.websocket("/alerts")
async def alerts_websocket(websocket: WebSocket) -> None:
    """Existing alerts broadcast channel."""
    await alerts_ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        alerts_ws_manager.disconnect(websocket)


@router.websocket("/camera")
async def camera_websocket(websocket: WebSocket) -> None:
    """ESP32-CAM connects here and streams binary JPEG frames."""
    await camera_mgr.connect(websocket)
    frame_idx      = 0
    t_last_log     = time.time()
    last_dets: list[dict] = []
    event_logic = EventLogic()
    sleep_evidence_pipeline = DriverEvidencePipeline(
        event_key="sleeping",
        alert_type=AlertType.SLEEPING,
    )
    phone_evidence_pipeline = DriverEvidencePipeline(
        event_key="using_phone",
        alert_type=AlertType.USING_PHONE,
    )
    sleep_trigger = SleepWindowTrigger(
        fps=settings.DRIVER_EVENT_EVIDENCE_FPS,
        window_seconds=settings.DRIVER_EVENT_EVIDENCE_SECONDS,
        occupancy_threshold=1.0,
    )
    phone_trigger = SleepWindowTrigger(
        fps=settings.DRIVER_EVENT_EVIDENCE_FPS,
        window_seconds=settings.DRIVER_EVENT_EVIDENCE_SECONDS,
        occupancy_threshold=1.0,
    )
    was_sleeping_event = False
    was_phone_event = False
    sleep_evidence_task: Optional[asyncio.Task] = None
    phone_evidence_task: Optional[asyncio.Task] = None
    last_event = "normal"
    last_confidence = 0.0
    current_event_started_at: Optional[float] = None
    last_sleeping_seen_at: Optional[float] = None
    last_sleeping_confidence = 0.0
    last_phone_seen_at: Optional[float] = None
    last_phone_confidence = 0.0
    last_drowsy_seen_at: Optional[float] = None
    last_drowsy_confidence = 0.0
    last_alert_sent_at: dict[str, float] = {}

    try:
        while True:
            data = await websocket.receive()

            # ── Text message (hello / pong / status) ─────────────────────────
            if "text" in data and data["text"]:
                try:
                    msg = json.loads(data["text"])
                    logger.info("[ESP32] text: %s", msg)

                    if msg.get("type") == "pong":
                        await frontend_mgr.broadcast(json.dumps({
                            "type": "esp32_stats",
                            **msg,
                        }))
                except Exception:
                    pass
                continue

            # ── Binary JPEG frame ─────────────────────────────────────────────
            jpeg_bytes: Optional[bytes] = data.get("bytes")
            if not jpeg_bytes:
                continue

            frame_idx += 1

            # ── Run YOLO every SKIP_FRAMES (in thread pool, non-blocking) ────
            if frame_idx % SKIP_FRAMES == 0:
                loop = asyncio.get_running_loop()
                raw_dets = await loop.run_in_executor(None, run_inference, jpeg_bytes)
                last_dets = _filter_detections(raw_dets)

            raw_event, raw_confidence = event_logic.classify(last_dets)
            now_monotonic = time.monotonic()
            prev_event = last_event

            if raw_event == "sleeping":
                last_sleeping_seen_at = now_monotonic
                last_sleeping_confidence = raw_confidence
                event = raw_event
                confidence = raw_confidence
            elif (
                last_sleeping_seen_at is not None
                and (now_monotonic - last_sleeping_seen_at)
                < settings.DRIVER_EVENT_SLEEPING_RELEASE_GRACE_SECONDS
            ):
                event = "sleeping"
                confidence = max(raw_confidence, last_sleeping_confidence)
            elif raw_event == "using_phone":
                last_phone_seen_at = now_monotonic
                last_phone_confidence = raw_confidence
                event = raw_event
                confidence = raw_confidence
            elif (
                last_phone_seen_at is not None
                and (now_monotonic - last_phone_seen_at)
                < settings.DRIVER_EVENT_PHONE_RELEASE_GRACE_SECONDS
            ):
                event = "using_phone"
                confidence = max(raw_confidence, last_phone_confidence)
            elif raw_event == "drowsy":
                last_drowsy_seen_at = now_monotonic
                last_drowsy_confidence = raw_confidence
                event = raw_event
                confidence = raw_confidence
            elif (
                last_drowsy_seen_at is not None
                and (now_monotonic - last_drowsy_seen_at)
                < settings.DRIVER_EVENT_DROWSY_RELEASE_GRACE_SECONDS
            ):
                event = "drowsy"
                confidence = max(raw_confidence, last_drowsy_confidence)
            else:
                event = raw_event
                confidence = raw_confidence

            if event != prev_event:
                if event in ALERT_EVENTS:
                    current_event_started_at = now_monotonic
                else:
                    current_event_started_at = None

            event_duration_ms = 0
            if event in ALERT_EVENTS and current_event_started_at is not None:
                event_duration_ms = int(max(0.0, now_monotonic - current_event_started_at) * 1000)

            is_sleeping_event = event == "sleeping"
            if is_sleeping_event:
                if not was_sleeping_event:
                    sleep_evidence_pipeline.reset_buffer()
                evidence_jpeg = _annotate_evidence_jpeg(
                    jpeg_bytes=jpeg_bytes,
                    detections=last_dets,
                    event=event,
                    duration_ms=event_duration_ms,
                    confidence=confidence,
                )
                sleep_evidence_pipeline.push_frame(evidence_jpeg)
            elif was_sleeping_event:
                sleep_evidence_pipeline.reset_buffer()

            is_phone_event = event == "using_phone"
            if is_phone_event:
                if not was_phone_event:
                    phone_evidence_pipeline.reset_buffer()
                evidence_jpeg = _annotate_evidence_jpeg(
                    jpeg_bytes=jpeg_bytes,
                    detections=last_dets,
                    event=event,
                    duration_ms=event_duration_ms,
                    confidence=confidence,
                )
                phone_evidence_pipeline.push_frame(evidence_jpeg)
            elif was_phone_event:
                phone_evidence_pipeline.reset_buffer()

            should_save_sleeping = sleep_trigger.update(is_sleeping_event)
            if should_save_sleeping:
                can_queue = sleep_evidence_task is None or sleep_evidence_task.done()
                if can_queue:
                    async def _persist_and_broadcast(conf: float) -> None:
                        loop = asyncio.get_running_loop()
                        saved_alert = await loop.run_in_executor(
                            None,
                            sleep_evidence_pipeline.save_event_alert,
                            conf,
                        )
                        if saved_alert is not None:
                            await alerts_ws_manager.broadcast(
                                {
                                    "event": "alert.created",
                                    "data": saved_alert,
                                }
                            )
                            await frontend_mgr.broadcast(
                                json.dumps(
                                    {
                                        "type": "alert_created",
                                        "data": saved_alert,
                                    }
                                )
                            )

                    sleep_evidence_task = asyncio.create_task(_persist_and_broadcast(confidence))
                else:
                    logger.info("Skipping sleeping evidence save trigger because previous save is still running")

            should_save_phone = phone_trigger.update(is_phone_event)
            if should_save_phone:
                can_queue = phone_evidence_task is None or phone_evidence_task.done()
                if can_queue:
                    async def _persist_phone_and_broadcast(conf: float) -> None:
                        loop = asyncio.get_running_loop()
                        saved_alert = await loop.run_in_executor(
                            None,
                            phone_evidence_pipeline.save_event_alert,
                            conf,
                        )
                        if saved_alert is not None:
                            await alerts_ws_manager.broadcast(
                                {
                                    "event": "alert.created",
                                    "data": saved_alert,
                                }
                            )
                            await frontend_mgr.broadcast(
                                json.dumps(
                                    {
                                        "type": "alert_created",
                                        "data": saved_alert,
                                    }
                                )
                            )

                    phone_evidence_task = asyncio.create_task(_persist_phone_and_broadcast(confidence))
                else:
                    logger.info("Skipping using_phone evidence save trigger because previous save is still running")

            was_sleeping_event = is_sleeping_event
            was_phone_event = is_phone_event

            if event in ALERT_EVENTS:
                min_alert_seconds_by_event = {
                    "using_phone": settings.DRIVER_EVENT_PHONE_MIN_ALERT_SECONDS,
                    "drowsy": settings.DRIVER_EVENT_DROWSY_MIN_ALERT_SECONDS,
                }
                min_alert_seconds = min_alert_seconds_by_event.get(event, 0.0)
                stable_seconds = (
                    (now_monotonic - current_event_started_at)
                    if current_event_started_at is not None
                    else 0.0
                )
                if stable_seconds < min_alert_seconds:
                    last_event = event
                    last_confidence = confidence
                    continue

                last_sent = last_alert_sent_at.get(event, 0.0)
                should_emit = (
                    event != prev_event
                    or (now_monotonic - last_sent)
                    >= settings.DRIVER_EVENT_ALERT_COOLDOWN_SECONDS
                )
                if should_emit:
                    alert_payload = {
                        "type": "driver_alert",
                        "event": event,
                        "confidence": round(confidence, 4),
                        "timestamp": time.time(),
                        "device": camera_mgr.device_id,
                        "frame_idx": frame_idx,
                        "detections": len(last_dets),
                    }
                    await frontend_mgr.broadcast(json.dumps(alert_payload))
                    await alerts_ws_manager.broadcast(
                        {
                            "event": "gateway.alert",
                            "data": {
                                "device_id": camera_mgr.device_id,
                                "event": event,
                                "confidence": round(confidence, 4),
                                "frame_idx": frame_idx,
                                "timestamp": alert_payload["timestamp"],
                            },
                        }
                    )
                    last_alert_sent_at[event] = now_monotonic

            last_event = event
            last_confidence = confidence

            # ── Encode and broadcast to viewers only when there are clients ──
            if frontend_mgr.has_clients:
                jpeg_b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
                payload = json.dumps(
                    {
                        "type": "frame",
                        "frame_idx": frame_idx,
                        "timestamp": time.time(),
                        "jpeg": jpeg_b64,
                        "detections": last_dets,
                        "driver_event": last_event,
                        "driver_confidence": round(last_confidence, 4),
                        "event_timing": {
                            "active": last_event in ALERT_EVENTS,
                            "event": last_event,
                            "started_at": current_event_started_at,
                            "duration_ms": event_duration_ms,
                            "confidence": round(last_confidence, 4),
                        },
                        "device": camera_mgr.device_id,
                    }
                )
                asyncio.ensure_future(frontend_mgr.broadcast(payload))

            now = time.time()
            if now - t_last_log >= 5.0:
                logger.info(
                    "[CAMERA] frame=%d  event=%s  conf=%.2f  dets=%d  viewers=%d",
                    frame_idx,
                    last_event,
                    last_confidence,
                    len(last_dets),
                    frontend_mgr.client_count,
                )
                t_last_log = now

    except WebSocketDisconnect:
        pass
    finally:
        camera_mgr.disconnect()
        event_logic.reset()
        if sleep_evidence_task is not None and not sleep_evidence_task.done():
            sleep_evidence_task.cancel()
        if phone_evidence_task is not None and not phone_evidence_task.done():
            phone_evidence_task.cancel()
        await frontend_mgr.broadcast(json.dumps({"type": "camera_offline"}))


@router.websocket("/frontend")
async def frontend_websocket(websocket: WebSocket) -> None:
    """Browser viewers connect here to receive live JPEG frames."""
    await frontend_mgr.connect(websocket)

    # Send current camera status immediately on connect
    await websocket.send_text(json.dumps({
        "type": "pong",
        "camera": camera_mgr.is_online,
        "clients": frontend_mgr.client_count,
        "device": camera_mgr.device_id,
    }))

    try:
        while True:
            text = await websocket.receive_text()
            try:
                cmd = json.loads(text)
            except Exception:
                continue

            cmd_type = cmd.get("type")

            if cmd_type == "ping":
                # Heartbeat response
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "camera": camera_mgr.is_online,
                    "clients": frontend_mgr.client_count,
                    "device": camera_mgr.device_id,
                }))

            elif cmd_type in ("set_quality", "set_framesize", "set_vflip", "set_hmirror", "set_camera"):
                # Forward camera control command to ESP32
                ok = await camera_mgr.send_command(cmd)
                await websocket.send_text(json.dumps({
                    "type": "ack",
                    "cmd": cmd_type,
                    "success": ok,
                }))

    except WebSocketDisconnect:
        pass
    finally:
        frontend_mgr.disconnect(websocket)

