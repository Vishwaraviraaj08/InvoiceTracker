import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings

logger = logging.getLogger(__name__)


class MongoDBManager:
    """Manages MongoDB connection lifecycle."""

    def __init__(self):
        self.client: AsyncIOMotorClient | None = None
        self.database: AsyncIOMotorDatabase | None = None
        self._connected = False

    async def connect(self):
        """Connect to MongoDB."""
        settings = get_settings()
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_uri)
            self.database = self.client[settings.mongodb_database]
            await self.client.admin.command('ping')
            self._connected = True
            logger.info(f"Connected to MongoDB: {settings.mongodb_database}")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client is not None:
            self.client.close()
            self._connected = False
            logger.info("Disconnected from MongoDB")

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if self.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.database

    def get_collection(self, name: str):
        """Get a collection by name."""
        return self.get_database()[name]


MongoDB = MongoDBManager()
_db_manager = MongoDB


def get_database():
    """Get the active database instance (sync helper)."""
    if _db_manager is None or not _db_manager._connected:
        raise RuntimeError("Database not initialized")
    return _db_manager.get_database()
