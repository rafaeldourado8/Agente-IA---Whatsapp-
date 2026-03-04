"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings.

    All values are loaded from environment variables.
    Defaults are suitable for local development with Docker Compose.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Application
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    TENANT_CONFIG_DIR: str = "./tenants"

    # Google Gemini AI
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_VISION_MODEL: str = "gemini-2.0-flash"
    GEMINI_AUDIO_MODEL: str = "gemini-2.0-flash"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_PASSWORD: str

    # Qdrant
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_COLLECTION_NAME: str = "conversations"

    # WAHA (WhatsApp HTTP API)
    WAHA_API_URL: str = "http://localhost:3000"
    WAHA_API_KEY: str = ""

    # Webhook Security
    WEBHOOK_SECRET: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()  # type: ignore[call-arg]
