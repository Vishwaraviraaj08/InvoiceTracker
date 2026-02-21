import logging
import random
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    groq_api_key: str = ""

    groq_models: List[str] = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3-groq-70b-8192-tool-use-preview",
    ]

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "invoice_tracker"

    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_random_model(self) -> str:
        """Get a random model from the available list for load distribution."""
        return random.choice(self.groq_models)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
