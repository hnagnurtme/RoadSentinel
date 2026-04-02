import os

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "development"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    WRITER_DB_URL: str = Field(
        default="mysql+aiomysql://fastapi:fastapi@localhost:3306/fastapi",
        validation_alias=AliasChoices("WRITER_DB_URL", "DATABASE_URL", "POSTGRES_URL"),
    )
    READER_DB_URL: str = Field(
        default="mysql+aiomysql://fastapi:fastapi@localhost:3306/fastapi",
        validation_alias=AliasChoices("READER_DB_URL", "DATABASE_URL", "POSTGRES_URL"),
    )
    JWT_SECRET_KEY: str = "fastapi"
    JWT_ALGORITHM: str = "HS256"
    SENTRY_SDN: str = ""
    CELERY_BROKER_URL: str = "amqp://user:bitnami@localhost:5672/"
    CELERY_BACKEND_URL: str = "redis://:password123@localhost:6379/0"
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL"),
    )
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on", "debug"}:
                return True
            if lowered in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    @model_validator(mode="after")
    def normalize_database_urls(self):
        self.WRITER_DB_URL = self._normalize_async_db_url(self.WRITER_DB_URL)
        self.READER_DB_URL = self._normalize_async_db_url(self.READER_DB_URL)
        return self

    @staticmethod
    def _normalize_async_db_url(url: str) -> str:
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://", 1)
        return url


class TestConfig(Config):
    WRITER_DB_URL: str = Field(
        default="mysql+aiomysql://fastapi:fastapi@localhost:3306/fastapi_test",
        validation_alias=AliasChoices("TEST_WRITER_DB_URL", "WRITER_DB_URL"),
    )
    READER_DB_URL: str = Field(
        default="mysql+aiomysql://fastapi:fastapi@localhost:3306/fastapi_test",
        validation_alias=AliasChoices("TEST_READER_DB_URL", "READER_DB_URL"),
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("TEST_REDIS_URL"),
    )


class LocalConfig(Config):
    ...


class ProductionConfig(Config):
    DEBUG: bool = False


def get_config():
    env = os.getenv("ENV", "local")
    config_type = {
        "test": TestConfig(),
        "local": LocalConfig(),
        "prod": ProductionConfig(),
    }
    return config_type[env]


config: Config = get_config()
