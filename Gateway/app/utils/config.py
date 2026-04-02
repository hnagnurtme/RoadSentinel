"""
config.py – Central configuration for the Gateway DMS.
All tuneable parameters live here so nothing is hard-coded elsewhere.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

try:
    import yaml
except ImportError:  # pragma: no cover - optional at runtime
    yaml = None


@dataclass
class CaptureConfig:
    # "webcam" uses the local camera, "esp32" uses an MJPEG/HTTP stream
    source: Literal["webcam", "esp32"] = "esp32"

    # Webcam device index (usually 0 for the built-in camera)
    webcam_index: int = 0

    # Full URL to the ESP32-CAM MJPEG stream
    esp32_url: str = "http://172.31.98.91:81/stream"

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
    min_sleep_confidence: float = 0.5
    min_phone_confidence: float = 0.6
    min_distracted_confidence: float = 0.6

    # Hysteresis thresholds: enter must be higher than exit to avoid flicker.
    sleep_enter_frames: int = 3
    sleep_exit_frames: int = 1
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
class CloudinaryConfig:
    # Upload enable flag.
    enabled: bool = False

    # Credentials loaded from env.yml or environment variables.
    cloud_name: str = ""
    api_key: str = ""
    api_secret: str = ""

    # Optional upload folder prefix on Cloudinary.
    folder: str = "roadsentinel/gateway"

    def __post_init__(self) -> None:
        if self.enabled:
            if not self.cloud_name:
                raise ValueError("cloudinary.cloud_name must not be empty")
            if not self.api_key:
                raise ValueError("cloudinary.api_key must not be empty")
            if not self.api_secret:
                raise ValueError("cloudinary.api_secret must not be empty")


@dataclass
class EvidenceConfig:
    # Toggle evidence recording.
    enabled: bool = True

    # Folder to store generated evidence clips.
    evidence_dir: str = "evidence"

    # Save one clip when sleeping lasts this many consecutive seconds.
    sleep_evidence_seconds: int = 8

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
    cloudinary: CloudinaryConfig = field(default_factory=CloudinaryConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)


# ---------------------------------------------------------------------------
# Singleton – import and use this object throughout the project
# ---------------------------------------------------------------------------
CONFIG = GatewayConfig()


def _load_capture_overrides_from_yaml() -> dict[str, object]:
    """Read optional capture overrides from config.yml (gateway.capture)."""
    config_file = Path(__file__).resolve().parents[2] / "config.yml"
    if not config_file.exists() or yaml is None:
        return {}

    try:
        raw = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

    if not isinstance(raw, dict):
        return {}

    gateway = raw.get("gateway")
    if not isinstance(gateway, dict):
        return {}

    capture = gateway.get("capture")
    if not isinstance(capture, dict):
        return {}

    allowed = {"source", "webcam_index", "esp32_url", "target_fps"}
    return {k: v for k, v in capture.items() if k in allowed}


def _load_capture_overrides_from_env() -> dict[str, object]:
    """Read optional capture overrides from environment variables."""
    out: dict[str, object] = {}

    source = os.getenv("GATEWAY_CAPTURE_SOURCE")
    if source:
        out["source"] = source

    webcam_index = os.getenv("GATEWAY_WEBCAM_INDEX")
    if webcam_index:
        out["webcam_index"] = int(webcam_index)

    esp32_url = os.getenv("GATEWAY_ESP32_URL")
    if esp32_url:
        out["esp32_url"] = esp32_url

    target_fps = os.getenv("GATEWAY_TARGET_FPS")
    if target_fps:
        out["target_fps"] = int(target_fps)

    return out


def _load_cloudinary_overrides_from_yaml() -> dict[str, object]:
    """Read optional Cloudinary credentials from env.yml (cloudinary.*)."""
    env_file = Path(__file__).resolve().parents[2] / "env.yml"
    if not env_file.exists() or yaml is None:
        return {}

    try:
        raw = yaml.safe_load(env_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

    if not isinstance(raw, dict):
        return {}

    cloudinary = raw.get("cloudinary")
    if not isinstance(cloudinary, dict):
        return {}

    allowed = {"enabled", "cloud_name", "api_key", "api_secret", "folder"}
    return {k: v for k, v in cloudinary.items() if k in allowed}


def _load_cloudinary_overrides_from_env() -> dict[str, object]:
    """Read optional Cloudinary credentials from environment variables."""
    out: dict[str, object] = {}

    enabled = os.getenv("CLOUDINARY_ENABLED")
    if enabled is not None:
        out["enabled"] = enabled.strip().lower() in {"1", "true", "yes", "on"}

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    if cloud_name:
        out["cloud_name"] = cloud_name

    api_key = os.getenv("CLOUDINARY_API_KEY")
    if api_key:
        out["api_key"] = api_key

    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    if api_secret:
        out["api_secret"] = api_secret

    folder = os.getenv("CLOUDINARY_FOLDER")
    if folder:
        out["folder"] = folder

    return out


def _apply_capture_overrides() -> None:
    """Apply non-invasive runtime overrides for capture config only."""
    overrides = {}
    overrides.update(_load_capture_overrides_from_yaml())
    overrides.update(_load_capture_overrides_from_env())
    if not overrides:
        return

    current = CONFIG.capture
    CONFIG.capture = CaptureConfig(
        source=overrides.get("source", current.source),
        webcam_index=int(overrides.get("webcam_index", current.webcam_index)),
        esp32_url=str(overrides.get("esp32_url", current.esp32_url)),
        target_fps=int(overrides.get("target_fps", current.target_fps)),
    )


def _apply_cloudinary_overrides() -> None:
    """Apply Cloudinary overrides from env.yml/env vars if present."""
    overrides = {}
    overrides.update(_load_cloudinary_overrides_from_yaml())
    overrides.update(_load_cloudinary_overrides_from_env())
    if not overrides:
        return

    current = CONFIG.cloudinary
    inferred_enabled = current.enabled
    if "enabled" in overrides:
        inferred_enabled = bool(overrides["enabled"])
    elif any(key in overrides for key in ("cloud_name", "api_key", "api_secret")):
        inferred_enabled = True

    CONFIG.cloudinary = CloudinaryConfig(
        enabled=inferred_enabled,
        cloud_name=str(overrides.get("cloud_name", current.cloud_name)),
        api_key=str(overrides.get("api_key", current.api_key)),
        api_secret=str(overrides.get("api_secret", current.api_secret)),
        folder=str(overrides.get("folder", current.folder)),
    )


_apply_capture_overrides()
_apply_cloudinary_overrides()
