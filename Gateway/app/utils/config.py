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
    # How many consecutive frames without a face/eyes before "sleeping"
    sleep_frame_threshold: int = 15

    def __post_init__(self) -> None:
        if self.sleep_frame_threshold <= 0:
            raise ValueError("event.sleep_frame_threshold must be > 0")


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
class GatewayConfig:
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    event: EventConfig = field(default_factory=EventConfig)
    sender: SenderConfig = field(default_factory=SenderConfig)


# ---------------------------------------------------------------------------
# Singleton – import and use this object throughout the project
# ---------------------------------------------------------------------------
CONFIG = GatewayConfig()
