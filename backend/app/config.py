"""
Application Configuration
Manages environment variables and application settings using Pydantic Settings
"""

from functools import lru_cache
from typing import List
import random

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Groq API
    groq_api_key: str = ""
    
    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "invoice_manager"
    
    # Application
    debug: bool = False
    log_level: str = "INFO"
    
    # Embedding Model
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Groq Models Pool for load distribution
    # Note: Excluding whisper (audio) and guard (safety) models
    groq_models: List[str] = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "qwen/qwen3-32b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "moonshotai/kimi-k2-instruct-0905",
        "canopylabs/orpheus-v1-english",
        "canopylabs/orpheus-arabic-saudi",
        "groq/compound",
        "groq/compound-mini"
    ]
    
    def get_random_model(self) -> str:
        """Select a random model from the pool for load distribution"""
        return random.choice(self.groq_models)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
