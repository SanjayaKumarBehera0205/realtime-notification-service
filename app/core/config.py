from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Real-Time Notification Service"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./notifications.db"
    secret_key: str = "change-this-secret-before-production"
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"
    redis_enabled: bool = False
    redis_url: str = "redis://localhost:6379/0"
    redis_channel: str = "notifications"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
