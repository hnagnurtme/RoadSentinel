from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Road Sentinel"
    APP_VERSION : str ="1.0.0"
    APP_ENV: Literal["development", "production", "testing"] = "development"
    DEBUG:bool  =True

    # CORS Allow Urls
    CORS_ALLOW_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS : bool = True

    # Database
    DATABASE_URL:str
    DB_POOL_SIZE : int  = 10

    # JWT Authentication
    JWT_SECRET_KEY :str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES : int =  30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS : int = 7

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        case_sensitive = True,
        extra="ignore"
    )

settings = Settings()