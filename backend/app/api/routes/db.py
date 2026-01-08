"""
Database Management Routes
Endpoints for database operations like clearing data
"""

from fastapi import APIRouter, HTTPException
from app.db.mongodb import MongoDB
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/db", tags=["database"])


@router.post("/clear")
@router.get("/clear")
async def clear_database():
    """
    Clear all data from the database.
    WARNING: This will delete all documents, embeddings, and validation results.
    Use with caution!
    """
    try:
        db = MongoDB.get_database()
        
        # Get all collection names
        collections = await db.list_collection_names()
        
        deleted_counts = {}
        
        # Drop each collection
        for collection_name in collections:
            result = await db[collection_name].delete_many({})
            deleted_counts[collection_name] = result.deleted_count
            logger.info(f"Cleared {result.deleted_count} documents from {collection_name}")
        
        total_deleted = sum(deleted_counts.values())
        
        return {
            "success": True,
            "message": f"Database cleared successfully. Deleted {total_deleted} total documents.",
            "details": deleted_counts
        }
    
    except Exception as e:
        logger.error(f"Failed to clear database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear database: {str(e)}")


@router.get("/stats")
async def get_database_stats():
    """Get database statistics (document counts per collection)"""
    try:
        db = MongoDB.get_database()
        collections = await db.list_collection_names()
        
        stats = {}
        for collection_name in collections:
            count = await db[collection_name].count_documents({})
            stats[collection_name] = count
        
        return {
            "success": True,
            "collections": stats,
            "total_documents": sum(stats.values())
        }
    
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
