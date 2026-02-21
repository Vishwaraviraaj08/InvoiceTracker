import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.mongodb import MongoDB
from app.api.middleware.logging import LoggingMiddleware
from app.api.middleware.error_handler import ErrorHandlerMiddleware
from app.api.routes import documents, validation, chat, analytics, exports, watcher, db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Invoice Manager API...")
    try:
        await MongoDB.connect()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    yield

    logger.info("Shutting down Invoice Manager API...")
    await MongoDB.disconnect()


app = FastAPI(
    title="Invoice Manager API",
    description="Production-grade Invoice Manager with LangChain, LangGraph, RAG, and MCP servers",
    version="1.0.0",
    lifespan=lifespan
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)

app.include_router(documents.router)
app.include_router(validation.router)
app.include_router(chat.router)
app.include_router(analytics.router)
app.include_router(exports.router)
app.include_router(watcher.router)
app.include_router(db.router)


@app.get("/")
async def root():
    return {
        "name": "Invoice Manager API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/cleardb")
@app.post("/cleardb")
async def clear_all_db_data():
    """Clear all data from the database. Use with caution!"""
    try:
        from app.db.mongodb import get_database
        from fastapi import HTTPException
        db = get_database()
        collections = await db.list_collection_names()

        deleted_counts = {}
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
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to clear database: {str(e)}")


@app.get("/health")
async def health_check():
    try:
        db_conn = MongoDB.get_database()
        await db_conn.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
