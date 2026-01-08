
import asyncio
import os
import sys

# Add parent directory to path to allow imports from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings

async def clear_database():
    settings = get_settings()
    print(f"Connecting to MongoDB at {settings.mongodb_uri}...")
    
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db_name = settings.mongodb_database
    
    print(f"Dropping database: {db_name}...")
    await client.drop_database(db_name)
    
    print("Database cleared successfully.")
    client.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(clear_database())
