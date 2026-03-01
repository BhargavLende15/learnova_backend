"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""
    MONGODB_URI: str = "mongodb://localhost:27017/learnova"
    OPENAI_API_KEY: str = ""
    JWT_SECRET: str = "learnova-dev-secret-change-in-production"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
