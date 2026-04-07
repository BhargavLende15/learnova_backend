"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""
    # SQLite by default for zero-config demo; set postgresql+asyncpg://... for PostgreSQL
    DATABASE_URL: str = "sqlite+aiosqlite:///./learnova.db"
    MONGODB_URI: str = ""  # Optional: mirror roadmaps / question bank
    OPENAI_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    JWT_SECRET: str = "learnova-dev-secret-change-in-production"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
