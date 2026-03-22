"""
config.py – Central configuration for the Gateway DMS.
All tuneable parameters live here so nothing is hard-coded elsewhere.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class CaptureConfig:
    # "webcam" uses the local camera, "esp32" uses an MJPEG/HTTP stream
    source: Literal["webcam", "esp32"] = "webcam"

    # Webcam device index (usually 0 for the built-in camera)
    webcam_index: int = 0

    # Full URL to the ESP32-CAM MJPEG stream
    esp32_url: str = "http://192.168.1.100/stream"

    # Target frames-per-second for the main capture loop
    target_fps: int = 5

    def __post_init__(self) -> None:
        if self.target_fps <= 0:
            raise ValueError("capture.target_fps must be > 0")
        if self.webcam_index < 0:
            raise ValueError("capture.webcam_index must be >= 0")


@dataclass
class PreprocessConfig:
    # Resolution fed to YOLO – smaller = faster inference
    width: int = 320
    height: int = 240

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("preprocess width/height must be > 0")


@dataclass
class InferenceConfig:
    # Path (relative to project root) to the YOLO weights file
    model_path: str = "models/best.pt"

    # Minimum confidence threshold to accept a detection
    confidence_threshold: float = 0.5

    # IOU threshold used by NMS
    iou_threshold: float = 0.45

    # Run on: "cpu" | "cuda" | "mps" (Apple Silicon)
    device: str = "cpu"

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("inference.confidence_threshold must be in [0, 1]")
        if not 0.0 <= self.iou_threshold <= 1.0:
            raise ValueError("inference.iou_threshold must be in [0, 1]")
        if not self.model_path:
            raise ValueError("inference.model_path must not be empty")


@dataclass
class EventConfig:
    # Labels used to decide if the driver is currently observable.
    presence_labels: tuple[str, ...] = ("face", "eye", "person", "driver")

    # Consecutive no-presence frames before emitting "unknown".
    unknown_enter_frames: int = 12

    # Evidence labels per event.
    sleep_labels: tuple[str, ...] = (
        "sleeping",
        "drowsy",
        "eyes closed",
        "yawning",
    )
    phone_labels: tuple[str, ...] = (
        "cell phone",
        "mobile",
        "texting",
        "driver talking on phone",
    )
    distracted_labels: tuple[str, ...] = (
        "distracted",
        "driver looking away",
        "driver reaching behind",
    )

    # Minimum confidence required to treat a label as evidence.
    min_sleep_confidence: float = 0.6
    min_phone_confidence: float = 0.6
    min_distracted_confidence: float = 0.6

    # Hysteresis thresholds: enter must be higher than exit to avoid flicker.
    sleep_enter_frames: int = 6
    sleep_exit_frames: int = 3
    phone_enter_frames: int = 3
    phone_exit_frames: int = 1
    distracted_enter_frames: int = 4
    distracted_exit_frames: int = 2

    # Priority order when multiple events are active.
    event_priority: tuple[str, ...] = ("using_phone", "sleeping", "distracted")

    def __post_init__(self) -> None:
        if self.unknown_enter_frames <= 0:
            raise ValueError("event.unknown_enter_frames must be > 0")

        for name, value in (
            ("event.min_sleep_confidence", self.min_sleep_confidence),
            ("event.min_phone_confidence", self.min_phone_confidence),
            ("event.min_distracted_confidence", self.min_distracted_confidence),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")

        for name, value in (
            ("event.sleep_enter_frames", self.sleep_enter_frames),
            ("event.sleep_exit_frames", self.sleep_exit_frames),
            ("event.phone_enter_frames", self.phone_enter_frames),
            ("event.phone_exit_frames", self.phone_exit_frames),
            ("event.distracted_enter_frames", self.distracted_enter_frames),
            ("event.distracted_exit_frames", self.distracted_exit_frames),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be > 0")

        if self.sleep_exit_frames > self.sleep_enter_frames:
            raise ValueError("event.sleep_exit_frames must be <= sleep_enter_frames")
        if self.phone_exit_frames > self.phone_enter_frames:
            raise ValueError("event.phone_exit_frames must be <= phone_enter_frames")
        if self.distracted_exit_frames > self.distracted_enter_frames:
            raise ValueError(
                "event.distracted_exit_frames must be <= distracted_enter_frames"
            )

        if not self.presence_labels:
            raise ValueError("event.presence_labels must not be empty")
        if not self.event_priority:
            raise ValueError("event.event_priority must not be empty")


@dataclass
class SenderConfig:
    # WebSocket endpoint on the backend server
    ws_url: str = "ws://localhost:8000/ws/gateway"

    # REST endpoint (fallback / HTTP mode)
    http_url: str = "http://localhost:8000/api/events"

    # Unique identifier for this gateway device
    device_id: str = "car_01"

    # Seconds to wait before retrying a failed connection
    reconnect_delay: float = 3.0

    # Maximum number of unsent payloads kept in memory
    queue_maxsize: int = 200

    def __post_init__(self) -> None:
        if not self.ws_url:
            raise ValueError("sender.ws_url must not be empty")
        if not self.http_url:
            raise ValueError("sender.http_url must not be empty")
        if not self.device_id:
            raise ValueError("sender.device_id must not be empty")
        if self.reconnect_delay < 0:
            raise ValueError("sender.reconnect_delay must be >= 0")
        if self.queue_maxsize <= 0:
            raise ValueError("sender.queue_maxsize must be > 0")


@dataclass
class EvidenceConfig:
    # Toggle evidence recording.
    enabled: bool = True

    # Folder to store generated evidence clips.
    evidence_dir: str = "evidence"

    # Save one clip when sleeping lasts this many consecutive seconds.
    sleep_evidence_seconds: int = 5

    # Trigger only when sleeping occupancy in the 10s window passes this ratio.
    sleep_trigger_ratio: float = 0.6

    # Fallback proxy when explicit sleep labels are unstable.
    use_sleep_proxy: bool = True
    min_presence_confidence: float = 0.4
    min_eyes_open_confidence: float = 0.6

    # Video codec for OpenCV VideoWriter (4 characters).
    codec: str = "mp4v"

    def __post_init__(self) -> None:
        if not self.evidence_dir:
            raise ValueError("evidence.evidence_dir must not be empty")
        if self.sleep_evidence_seconds <= 0:
            raise ValueError("evidence.sleep_evidence_seconds must be > 0")
        if not 0.0 < self.sleep_trigger_ratio <= 1.0:
            raise ValueError("evidence.sleep_trigger_ratio must be in (0, 1]")
        if not 0.0 <= self.min_presence_confidence <= 1.0:
            raise ValueError("evidence.min_presence_confidence must be in [0, 1]")
        if not 0.0 <= self.min_eyes_open_confidence <= 1.0:
            raise ValueError("evidence.min_eyes_open_confidence must be in [0, 1]")
        if len(self.codec) != 4:
            raise ValueError("evidence.codec must be exactly 4 characters")


@dataclass
class GatewayConfig:
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    event: EventConfig = field(default_factory=EventConfig)
    sender: SenderConfig = field(default_factory=SenderConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)


# ---------------------------------------------------------------------------
# Singleton – import and use this object throughout the project
# ---------------------------------------------------------------------------
CONFIG = GatewayConfig()
