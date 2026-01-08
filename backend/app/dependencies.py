"""
Dependency Injection for FastAPI
Provides database connections, services, and other dependencies
"""

from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings


_mongo_client: AsyncIOMotorClient | None = None


async def get_database() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Get MongoDB database instance"""
    global _mongo_client
    
    settings = get_settings()
    
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(settings.mongodb_uri)
    
    yield _mongo_client[settings.mongodb_database]


async def startup_db():
    """Initialize database connection on startup"""
    global _mongo_client
    settings = get_settings()
    _mongo_client = AsyncIOMotorClient(settings.mongodb_uri)


async def shutdown_db():
    """Close database connection on shutdown"""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
