from functools import lru_cache
from typing import Any
import os
from pathlib import Path
import uuid

from dotenv import load_dotenv
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    import yaml
except ImportError:  # pragma: no cover - optional runtime dependency
    yaml = None

load_dotenv()


def _apply_gateway_cloudinary_defaults() -> None:
    """
    Keep backend cloudinary config in sync with Gateway env.yml when backend
    variables are not explicitly provided.
    """
    if yaml is None:
        return

    root_dir = Path(__file__).resolve().parents[2]
    env_yml = root_dir / "Gateway" / "env.yml"
    if not env_yml.exists():
        return

    try:
        raw = yaml.safe_load(env_yml.read_text(encoding="utf-8")) or {}
    except Exception:
        return

    if not isinstance(raw, dict):
        return

    cloud = raw.get("cloudinary")
    if not isinstance(cloud, dict):
        return

    mappings = {
        "DRIVER_EVENT_CLOUDINARY_CLOUD_NAME": cloud.get("cloud_name"),
        "DRIVER_EVENT_CLOUDINARY_API_KEY": cloud.get("api_key"),
        "DRIVER_EVENT_CLOUDINARY_API_SECRET": cloud.get("api_secret"),
        "DRIVER_EVENT_CLOUDINARY_FOLDER": cloud.get("folder"),
    }

    found_any_credential = False
    for env_key, value in mappings.items():
        if os.getenv(env_key):
            continue
        if value is None:
            continue
        normalized = str(value).strip()
        if not normalized:
            continue
        os.environ[env_key] = normalized
        if env_key in {
            "DRIVER_EVENT_CLOUDINARY_CLOUD_NAME",
            "DRIVER_EVENT_CLOUDINARY_API_KEY",
            "DRIVER_EVENT_CLOUDINARY_API_SECRET",
        }:
            found_any_credential = True

    if (
        found_any_credential
        and os.getenv("DRIVER_EVENT_CLOUDINARY_ENABLED") is None
        and cloud.get("enabled") is None
    ):
        os.environ["DRIVER_EVENT_CLOUDINARY_ENABLED"] = "true"

    if os.getenv("DRIVER_EVENT_CLOUDINARY_ENABLED") is None and cloud.get("enabled") is not None:
        enabled = str(cloud.get("enabled")).strip().lower()
        os.environ["DRIVER_EVENT_CLOUDINARY_ENABLED"] = (
            "true" if enabled in {"1", "true", "yes", "on"} else "false"
        )


_apply_gateway_cloudinary_defaults()


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

    CORS_ALLOW_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    DRIVER_EVENT_UNKNOWN_ENTER_FRAMES: int = 12

    DRIVER_EVENT_SLEEP_ENTER_FRAMES: int = 3
    DRIVER_EVENT_SLEEP_EXIT_FRAMES: int = 1
    DRIVER_EVENT_PHONE_ENTER_FRAMES: int = 3
    DRIVER_EVENT_PHONE_EXIT_FRAMES: int = 1
    DRIVER_EVENT_DISTRACTED_ENTER_FRAMES: int = 4
    DRIVER_EVENT_DISTRACTED_EXIT_FRAMES: int = 2
    DRIVER_EVENT_DROWSY_ENTER_FRAMES: int = 3
    DRIVER_EVENT_DROWSY_EXIT_FRAMES: int = 1

    DRIVER_EVENT_PHONE_DECAY_MISS_FRAMES: int = 2
    DRIVER_EVENT_DROWSY_DECAY_MISS_FRAMES: int = 2

    DRIVER_EVENT_MIN_SLEEP_CONFIDENCE: float = 0.5
    DRIVER_EVENT_MIN_PHONE_CONFIDENCE: float = 0.6
    DRIVER_EVENT_MIN_DISTRACTED_CONFIDENCE: float = 0.6
    DRIVER_EVENT_MIN_DROWSY_CONFIDENCE: float = 0.55

    DRIVER_EVENT_PRESENCE_LABELS: list[str] = ["face", "eye", "person", "driver"]
    DRIVER_EVENT_PRIORITY: list[str] = ["using_phone", "sleeping", "distracted"]

    DRIVER_EVENT_SLEEPING_RELEASE_GRACE_SECONDS: float = 1.0
    DRIVER_EVENT_PHONE_RELEASE_GRACE_SECONDS: float = 0.8
    DRIVER_EVENT_DROWSY_RELEASE_GRACE_SECONDS: float = 0.8
    DRIVER_EVENT_ALERT_COOLDOWN_SECONDS: float = 2.0
    DRIVER_EVENT_PHONE_MIN_ALERT_SECONDS: float = 1.2
    DRIVER_EVENT_DROWSY_MIN_ALERT_SECONDS: float = 1.5

    DRIVER_EVENT_EVIDENCE_ENABLED: bool = True
    DRIVER_EVENT_EVIDENCE_SECONDS: int = 8
    DRIVER_EVENT_EVIDENCE_FPS: int = 5
    DRIVER_EVENT_EVIDENCE_CODEC: str = "mp4v"

    DRIVER_EVENT_CLOUDINARY_ENABLED: bool = False
    DRIVER_EVENT_CLOUDINARY_CLOUD_NAME: str = ""
    DRIVER_EVENT_CLOUDINARY_API_KEY: str = ""
    DRIVER_EVENT_CLOUDINARY_API_SECRET: str = ""
    DRIVER_EVENT_CLOUDINARY_FOLDER: str = "roadsentinel/backend"

    DRIVER_EVENT_ALERT_DEVICE_ID: uuid.UUID = uuid.UUID(
        "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    )
    DRIVER_EVENT_ALERT_DRIVER_ID: uuid.UUID | None = uuid.UUID(
        "1edc79dd-1331-454e-b64d-12fb8e77f464"
    )
    DRIVER_EVENT_ALERT_VEHICLE_ID: uuid.UUID | None = uuid.UUID(
        "0e225dd7-deba-4cfa-91ef-dfa30a3942d1"
    )

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
    )
    @classmethod
    def _validate_confidence(cls, value: float) -> float:
        if value < 0.0 or value > 1.0:
            raise ValueError("Driver event confidence thresholds must be in [0, 1]")
        return value

    @field_validator(
        "DRIVER_EVENT_SLEEPING_RELEASE_GRACE_SECONDS",
        "DRIVER_EVENT_PHONE_RELEASE_GRACE_SECONDS",
        "DRIVER_EVENT_DROWSY_RELEASE_GRACE_SECONDS",
        "DRIVER_EVENT_ALERT_COOLDOWN_SECONDS",
        "DRIVER_EVENT_PHONE_MIN_ALERT_SECONDS",
        "DRIVER_EVENT_DROWSY_MIN_ALERT_SECONDS",
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
                ("DRIVER_EVENT_CLOUDINARY_CLOUD_NAME", self.DRIVER_EVENT_CLOUDINARY_CLOUD_NAME),
                ("DRIVER_EVENT_CLOUDINARY_API_KEY", self.DRIVER_EVENT_CLOUDINARY_API_KEY),
                ("DRIVER_EVENT_CLOUDINARY_API_SECRET", self.DRIVER_EVENT_CLOUDINARY_API_SECRET),
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
        allowed = {"sleeping", "using_phone", "distracted"}
        priority = [item.strip().lower() for item in value if item and item.strip()]
        if not priority:
            raise ValueError("DRIVER_EVENT_PRIORITY must not be empty")
        if any(event not in allowed for event in priority):
            raise ValueError(
                "DRIVER_EVENT_PRIORITY only supports: sleeping, using_phone, distracted"
            )
        return priority


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
