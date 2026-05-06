import json
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    import yaml
except ImportError:
    yaml = None

load_dotenv()


_SECRET_KEYS = {
    "DATABASE_URL",
    "REDIS_URL",
    "POSTGRES_URL",
    "DRIVER_EVENT_CLOUDINARY_API_KEY",
    "DRIVER_EVENT_CLOUDINARY_API_SECRET",
}


def _to_env_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return json.dumps(value)
    return str(value).strip()


def _flatten_yaml(prefix: str, value: Any, out: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key).strip().upper()
            if not key_text:
                continue
            next_prefix = f"{prefix}_{key_text}" if prefix else key_text
            _flatten_yaml(next_prefix, nested, out)
        return
    out[prefix] = value


def _apply_config_yaml_defaults() -> None:
    """Load non-secret application settings from config.yaml."""
    if yaml is None:
        return

    backend_root = Path(__file__).resolve().parents[1]
    config_path = backend_root / "config.yaml"
    if not config_path.exists():
        return

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return

    if not isinstance(raw, dict):
        return

    flattened: dict[str, Any] = {}
    _flatten_yaml("", raw, flattened)

    for env_key, value in flattened.items():
        if not env_key or env_key in _SECRET_KEYS:
            continue
        if os.getenv(env_key):
            continue
        if value is None:
            continue
        normalized = _to_env_value(value)
        if not normalized:
            continue
        os.environ[env_key] = normalized


_apply_config_yaml_defaults()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "RoadSentinel Backend"
    APP_ENV: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    APP_PUBLIC_BASE_URL: str = "http://127.0.0.1:8000"

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/roadsentinel"
    SQL_ECHO: bool = False

    CORS_ALLOW_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    DRIVER_EVENT_UNKNOWN_ENTER_FRAMES: int = 12

    # Sleeping detected in 2 frames — fast response is critical.
    DRIVER_EVENT_SLEEP_ENTER_FRAMES: int = 2
    DRIVER_EVENT_SLEEP_EXIT_FRAMES: int = 1
    DRIVER_EVENT_PHONE_ENTER_FRAMES: int = 3
    DRIVER_EVENT_PHONE_EXIT_FRAMES: int = 2
    # Distracted needs 6 sustained frames — brief glances away are normal.
    DRIVER_EVENT_DISTRACTED_ENTER_FRAMES: int = 6
    DRIVER_EVENT_DISTRACTED_EXIT_FRAMES: int = 2
    # Drowsy (yawning) needs 4 frames — yawning alone is not sleeping.
    DRIVER_EVENT_DROWSY_ENTER_FRAMES: int = 4
    DRIVER_EVENT_DROWSY_EXIT_FRAMES: int = 2

    DRIVER_EVENT_PHONE_DECAY_MISS_FRAMES: int = 2
    DRIVER_EVENT_DROWSY_DECAY_MISS_FRAMES: int = 2

    # Hierarchical sliding windows (in classifier ticks, not wall-clock frames).
    DRIVER_EVENT_L1_WINDOW_FRAMES: int = 3
    DRIVER_EVENT_L2_WINDOW_FRAMES: int = 9
    DRIVER_EVENT_L3_WINDOW_FRAMES: int = 24
    DRIVER_EVENT_WINDOW_DECAY: float = 0.82
    DRIVER_EVENT_SCORE_WEIGHT_L1: float = 0.45
    DRIVER_EVENT_SCORE_WEIGHT_L2: float = 0.40
    DRIVER_EVENT_SCORE_WEIGHT_L3: float = 0.15
    DRIVER_EVENT_CANDIDATE_ENTER_FRAMES: int = 1

    # Score-based activation/deactivation thresholds per event.
    DRIVER_EVENT_SLEEPING_ACTIVATE_SCORE: float = 0.55
    DRIVER_EVENT_SLEEPING_DEACTIVATE_SCORE: float = 0.35
    DRIVER_EVENT_PHONE_ACTIVATE_SCORE: float = 0.52
    DRIVER_EVENT_PHONE_DEACTIVATE_SCORE: float = 0.32
    DRIVER_EVENT_DISTRACTED_ACTIVATE_SCORE: float = 0.48
    DRIVER_EVENT_DISTRACTED_DEACTIVATE_SCORE: float = 0.30
    DRIVER_EVENT_DROWSY_ACTIVATE_SCORE: float = 0.52
    DRIVER_EVENT_DROWSY_DEACTIVATE_SCORE: float = 0.32

    # One-frame promotion when confidence is very high (eye-closed-like feel).
    DRIVER_EVENT_PHONE_FASTPATH_CONFIDENCE: float = 0.80
    DRIVER_EVENT_DISTRACTED_FASTPATH_CONFIDENCE: float = 0.78
    DRIVER_EVENT_DROWSY_FASTPATH_CONFIDENCE: float = 0.82

    # Hold frames keep an event alive briefly when score dips near threshold.
    DRIVER_EVENT_SLEEP_HOLD_FRAMES: int = 5
    DRIVER_EVENT_PHONE_HOLD_FRAMES: int = 3
    DRIVER_EVENT_DISTRACTED_HOLD_FRAMES: int = 4
    DRIVER_EVENT_DROWSY_HOLD_FRAMES: int = 3

    DRIVER_EVENT_MIN_SLEEP_CONFIDENCE: float = 0.5
    DRIVER_EVENT_MIN_PHONE_CONFIDENCE: float = 0.6
    DRIVER_EVENT_MIN_DISTRACTED_CONFIDENCE: float = 0.6
    DRIVER_EVENT_MIN_DROWSY_CONFIDENCE: float = 0.55

    DRIVER_EVENT_PRESENCE_LABELS: list[str] = ["face", "eye", "person", "driver"]
    DRIVER_EVENT_PRIORITY: list[str] = ["using_phone", "sleeping", "distracted"]

    DRIVER_EVENT_SLEEPING_RELEASE_GRACE_SECONDS: float = 1.5
    DRIVER_EVENT_PHONE_RELEASE_GRACE_SECONDS: float = 1.0
    DRIVER_EVENT_DISTRACTED_RELEASE_GRACE_SECONDS: float = 1.2
    DRIVER_EVENT_DROWSY_RELEASE_GRACE_SECONDS: float = 0.8
    # Cooldown between repeated alerts for the same event type.
    DRIVER_EVENT_ALERT_COOLDOWN_SECONDS: float = 3.0
    DRIVER_EVENT_PHONE_MIN_ALERT_SECONDS: float = 1.5
    DRIVER_EVENT_DROWSY_MIN_ALERT_SECONDS: float = 2.0
    # Sustained drowsy for this many seconds → escalate to sleeping-level urgency.
    DRIVER_EVENT_DROWSY_ESCALATION_SECONDS: float = 10.0

    DRIVER_EVENT_EVIDENCE_ENABLED: bool = True
    # 10 seconds of evidence gives enough context to judge an event.
    DRIVER_EVENT_EVIDENCE_SECONDS: int = 10
    DRIVER_EVENT_EVIDENCE_FPS: int = 5
    DRIVER_EVENT_EVIDENCE_CODEC: str = "mp4v"
    DRIVER_EVENT_EVIDENCE_CODEC_CANDIDATES: list[str] = ["avc1", "H264", "mp4v"]
    DRIVER_EVENT_EVIDENCE_KEEP_LOCAL_AFTER_UPLOAD: bool = False

    DRIVER_EVENT_CLOUDINARY_ENABLED: bool = False
    DRIVER_EVENT_CLOUDINARY_CLOUD_NAME: str = ""
    DRIVER_EVENT_CLOUDINARY_API_KEY: str = ""
    DRIVER_EVENT_CLOUDINARY_API_SECRET: str = ""
    DRIVER_EVENT_CLOUDINARY_FOLDER: str = "roadsentinel/backend"

    MQTT_ENABLED: bool = True
    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_TOPIC_PREFIX: str = "roadsentinel/alerts"
    MQTT_USERNAME: str | None = None
    MQTT_PASSWORD: str | None = None
    MQTT_TLS_ENABLED: bool = False
    MQTT_RECOVERY_STABLE_SECONDS: float = 3.0

    DRIVER_EVENT_FALLBACK_DEVICE_ID: uuid.UUID = uuid.UUID(
        "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    )
    DRIVER_EVENT_FALLBACK_DRIVER_ID: uuid.UUID | None = uuid.UUID(
        "c8307945-4ac3-4877-bc7c-067c5aca27cb"
    )
    DRIVER_EVENT_FALLBACK_VEHICLE_ID: uuid.UUID | None = uuid.UUID(
        "0e225dd7-deba-4cfa-91ef-dfa30a3942d1"
    )

    DRIVER_EVENT_ALERT_DEVICE_ID: uuid.UUID = uuid.UUID(
        "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    )
    DRIVER_EVENT_ALERT_DRIVER_ID: uuid.UUID | None = uuid.UUID(
        "c8307945-4ac3-4877-bc7c-067c5aca27cb"
    )
    DRIVER_EVENT_ALERT_VEHICLE_ID: uuid.UUID | None = uuid.UUID(
        "0e225dd7-deba-4cfa-91ef-dfa30a3942d1"
    )

    JWT_SECRET_KEY: str = "roadsentinel-dev-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  #

    @classmethod
    def _split_csv(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return value
        return []

    @field_validator(
        "CORS_ALLOW_ORIGINS",
        "CORS_ALLOW_METHODS",
        "CORS_ALLOW_HEADERS",
        "DRIVER_EVENT_PRESENCE_LABELS",
        "DRIVER_EVENT_PRIORITY",
        "DRIVER_EVENT_EVIDENCE_CODEC_CANDIDATES",
        mode="before",
    )
    @classmethod
    def _parse_cors_lists(cls, value: Any) -> list[str]:
        return cls._split_csv(value)

    @field_validator(
        "DRIVER_EVENT_UNKNOWN_ENTER_FRAMES",
        "DRIVER_EVENT_SLEEP_ENTER_FRAMES",
        "DRIVER_EVENT_SLEEP_EXIT_FRAMES",
        "DRIVER_EVENT_PHONE_ENTER_FRAMES",
        "DRIVER_EVENT_PHONE_EXIT_FRAMES",
        "DRIVER_EVENT_DISTRACTED_ENTER_FRAMES",
        "DRIVER_EVENT_DISTRACTED_EXIT_FRAMES",
        "DRIVER_EVENT_DROWSY_ENTER_FRAMES",
        "DRIVER_EVENT_DROWSY_EXIT_FRAMES",
        "DRIVER_EVENT_PHONE_DECAY_MISS_FRAMES",
        "DRIVER_EVENT_DROWSY_DECAY_MISS_FRAMES",
        "DRIVER_EVENT_L1_WINDOW_FRAMES",
        "DRIVER_EVENT_L2_WINDOW_FRAMES",
        "DRIVER_EVENT_L3_WINDOW_FRAMES",
        "DRIVER_EVENT_CANDIDATE_ENTER_FRAMES",
        "DRIVER_EVENT_SLEEP_HOLD_FRAMES",
        "DRIVER_EVENT_PHONE_HOLD_FRAMES",
        "DRIVER_EVENT_DISTRACTED_HOLD_FRAMES",
        "DRIVER_EVENT_DROWSY_HOLD_FRAMES",
        "MQTT_PORT",
    )
    @classmethod
    def _validate_positive_frames(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Driver event frame thresholds must be > 0")
        return value

    @field_validator(
        "DRIVER_EVENT_MIN_SLEEP_CONFIDENCE",
        "DRIVER_EVENT_MIN_PHONE_CONFIDENCE",
        "DRIVER_EVENT_MIN_DISTRACTED_CONFIDENCE",
        "DRIVER_EVENT_MIN_DROWSY_CONFIDENCE",
        "DRIVER_EVENT_WINDOW_DECAY",
        "DRIVER_EVENT_SCORE_WEIGHT_L1",
        "DRIVER_EVENT_SCORE_WEIGHT_L2",
        "DRIVER_EVENT_SCORE_WEIGHT_L3",
        "DRIVER_EVENT_SLEEPING_ACTIVATE_SCORE",
        "DRIVER_EVENT_SLEEPING_DEACTIVATE_SCORE",
        "DRIVER_EVENT_PHONE_ACTIVATE_SCORE",
        "DRIVER_EVENT_PHONE_DEACTIVATE_SCORE",
        "DRIVER_EVENT_DISTRACTED_ACTIVATE_SCORE",
        "DRIVER_EVENT_DISTRACTED_DEACTIVATE_SCORE",
        "DRIVER_EVENT_DROWSY_ACTIVATE_SCORE",
        "DRIVER_EVENT_DROWSY_DEACTIVATE_SCORE",
        "DRIVER_EVENT_PHONE_FASTPATH_CONFIDENCE",
        "DRIVER_EVENT_DISTRACTED_FASTPATH_CONFIDENCE",
        "DRIVER_EVENT_DROWSY_FASTPATH_CONFIDENCE",
    )
    @classmethod
    def _validate_confidence(cls, value: float) -> float:
        if value < 0.0 or value > 1.0:
            raise ValueError("Driver event confidence thresholds must be in [0, 1]")
        return value

    @field_validator(
        "DRIVER_EVENT_SLEEPING_RELEASE_GRACE_SECONDS",
        "DRIVER_EVENT_PHONE_RELEASE_GRACE_SECONDS",
        "DRIVER_EVENT_DISTRACTED_RELEASE_GRACE_SECONDS",
        "DRIVER_EVENT_DROWSY_RELEASE_GRACE_SECONDS",
        "DRIVER_EVENT_ALERT_COOLDOWN_SECONDS",
        "DRIVER_EVENT_PHONE_MIN_ALERT_SECONDS",
        "DRIVER_EVENT_DROWSY_MIN_ALERT_SECONDS",
        "DRIVER_EVENT_DROWSY_ESCALATION_SECONDS",
        "MQTT_RECOVERY_STABLE_SECONDS",
    )
    @classmethod
    def _validate_non_negative_seconds(cls, value: float) -> float:
        if value < 0.0:
            raise ValueError("Driver event timing values must be >= 0")
        return value

    @field_validator("DRIVER_EVENT_EVIDENCE_SECONDS", "DRIVER_EVENT_EVIDENCE_FPS")
    @classmethod
    def _validate_evidence_positive_ints(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Driver event evidence values must be > 0")
        return value

    @field_validator("DRIVER_EVENT_EVIDENCE_CODEC")
    @classmethod
    def _validate_evidence_codec(cls, value: str) -> str:
        if len(value) != 4:
            raise ValueError("DRIVER_EVENT_EVIDENCE_CODEC must be exactly 4 chars")
        return value

    @field_validator("DRIVER_EVENT_EVIDENCE_CODEC_CANDIDATES", mode="after")
    @classmethod
    def _validate_evidence_codec_candidates(cls, value: list[str]) -> list[str]:
        codecs = [item.strip() for item in value if item and item.strip()]
        if not codecs:
            raise ValueError("DRIVER_EVENT_EVIDENCE_CODEC_CANDIDATES must not be empty")
        for codec in codecs:
            if len(codec) != 4:
                raise ValueError(
                    "Each DRIVER_EVENT_EVIDENCE_CODEC_CANDIDATES value must be exactly 4 chars"
                )
        return codecs

    @field_validator(
        "DRIVER_EVENT_CLOUDINARY_CLOUD_NAME",
        "DRIVER_EVENT_CLOUDINARY_API_KEY",
        "DRIVER_EVENT_CLOUDINARY_API_SECRET",
        "DRIVER_EVENT_CLOUDINARY_FOLDER",
        mode="before",
    )
    @classmethod
    def _normalize_cloudinary_strings(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @field_validator(
        "MQTT_BROKER",
        "MQTT_TOPIC_PREFIX",
        "MQTT_USERNAME",
        "MQTT_PASSWORD",
        mode="before",
    )
    @classmethod
    def _normalize_mqtt_strings(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @field_validator("APP_PUBLIC_BASE_URL", mode="before")
    @classmethod
    def _normalize_public_base_url(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip().rstrip("/")
        return str(value).strip().rstrip("/")

    @model_validator(mode="after")
    def _validate_cloudinary_enabled(self):
        if not self.DRIVER_EVENT_CLOUDINARY_ENABLED:
            return self

        missing = [
            key
            for key, value in (
                (
                    "DRIVER_EVENT_CLOUDINARY_CLOUD_NAME",
                    self.DRIVER_EVENT_CLOUDINARY_CLOUD_NAME,
                ),
                (
                    "DRIVER_EVENT_CLOUDINARY_API_KEY",
                    self.DRIVER_EVENT_CLOUDINARY_API_KEY,
                ),
                (
                    "DRIVER_EVENT_CLOUDINARY_API_SECRET",
                    self.DRIVER_EVENT_CLOUDINARY_API_SECRET,
                ),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "Cloudinary is enabled but missing settings: " + ", ".join(missing)
            )
        return self

    @field_validator("DRIVER_EVENT_PRESENCE_LABELS", mode="after")
    @classmethod
    def _validate_presence_labels(cls, value: list[str]) -> list[str]:
        labels = [item.strip().lower() for item in value if item and item.strip()]
        if not labels:
            raise ValueError("DRIVER_EVENT_PRESENCE_LABELS must not be empty")
        return labels

    @field_validator("DRIVER_EVENT_PRIORITY", mode="after")
    @classmethod
    def _validate_event_priority(cls, value: list[str]) -> list[str]:
        allowed = {"sleeping", "using_phone", "distracted", "drowsy"}
        priority = [item.strip().lower() for item in value if item and item.strip()]
        if not priority:
            raise ValueError("DRIVER_EVENT_PRIORITY must not be empty")
        if any(event not in allowed for event in priority):
            raise ValueError(
                "DRIVER_EVENT_PRIORITY only supports: sleeping, using_phone, distracted, drowsy"
            )
        return priority

    @model_validator(mode="after")
    def _validate_hierarchical_windows(self):
        if not (
            self.DRIVER_EVENT_L1_WINDOW_FRAMES
            <= self.DRIVER_EVENT_L2_WINDOW_FRAMES
            <= self.DRIVER_EVENT_L3_WINDOW_FRAMES
        ):
            raise ValueError("Driver event windows must satisfy L1 <= L2 <= L3")

        weight_sum = (
            self.DRIVER_EVENT_SCORE_WEIGHT_L1
            + self.DRIVER_EVENT_SCORE_WEIGHT_L2
            + self.DRIVER_EVENT_SCORE_WEIGHT_L3
        )
        if weight_sum <= 0.0:
            raise ValueError("Driver event score weights must sum to > 0")

        pairs = (
            (
                "sleeping",
                self.DRIVER_EVENT_SLEEPING_ACTIVATE_SCORE,
                self.DRIVER_EVENT_SLEEPING_DEACTIVATE_SCORE,
            ),
            (
                "using_phone",
                self.DRIVER_EVENT_PHONE_ACTIVATE_SCORE,
                self.DRIVER_EVENT_PHONE_DEACTIVATE_SCORE,
            ),
            (
                "distracted",
                self.DRIVER_EVENT_DISTRACTED_ACTIVATE_SCORE,
                self.DRIVER_EVENT_DISTRACTED_DEACTIVATE_SCORE,
            ),
            (
                "drowsy",
                self.DRIVER_EVENT_DROWSY_ACTIVATE_SCORE,
                self.DRIVER_EVENT_DROWSY_DEACTIVATE_SCORE,
            ),
        )
        for event, activate, deactivate in pairs:
            if deactivate >= activate:
                raise ValueError(
                    f"{event} deactivate score must be lower than activate score"
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
