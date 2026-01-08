"""
MongoDB Connection Manager
Async MongoDB client using Motor driver
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager"""
    
    client: AsyncIOMotorClient | None = None
    database: AsyncIOMotorDatabase | None = None
    
    @classmethod
    async def connect(cls) -> None:
        """Establish MongoDB connection"""
        settings = get_settings()
        
        try:
            cls.client = AsyncIOMotorClient(settings.mongodb_uri)
            # Verify connection
            await cls.client.admin.command('ping')
            cls.database = cls.client[settings.mongodb_database]
            logger.info(f"Connected to MongoDB: {settings.mongodb_database}")
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise
    
    @classmethod
    async def disconnect(cls) -> None:
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if cls.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls.database
    
    @classmethod
    def get_collection(cls, name: str):
        """Get a collection by name"""
        return cls.get_database()[name]


def get_database() -> AsyncIOMotorDatabase:
    """Standalone helper to get database instance"""
    return MongoDB.get_database()

