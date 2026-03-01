"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "WeatherVault API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://weather_user:weather_pass@localhost:5432/weatherdb"

    # External APIs
    OPENWEATHER_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""

    # Cache
    WEATHER_CACHE_TTL_MINUTES: int = 10

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # Export
    EXPORT_DIR: str = "exports"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
