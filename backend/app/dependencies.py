import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.db.mongodb import MongoDBManager

logger = logging.getLogger(__name__)

_db_manager: MongoDBManager | None = None


async def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency: get database instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = MongoDBManager()
    if not _db_manager._connected:
        await _db_manager.connect()
    return _db_manager.get_database()


async def startup_db():
    """Initialize database connection on app startup."""
    global _db_manager
    _db_manager = MongoDBManager()
    await _db_manager.connect()
    logger.info("Database initialized")


async def shutdown_db():
    """Close database connection on app shutdown."""
    global _db_manager
    if _db_manager:
        await _db_manager.disconnect()
        logger.info("Database connection closed")
