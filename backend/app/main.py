"""
Invoice Manager - FastAPI Application Entry Point
Production-grade AI system with LangChain, LangGraph, RAG, and MCP servers
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.mongodb import MongoDB
from app.api.middleware.logging import LoggingMiddleware
from app.api.middleware.error_handler import ErrorHandlerMiddleware
from app.api.routes import documents, validation, chat, analytics, exports, watcher, db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Invoice Manager API...")
    
    try:
        await MongoDB.connect()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Invoice Manager API...")
    await MongoDB.disconnect()


# Create FastAPI app
app = FastAPI(
    title="Invoice Manager API",
    description="Production-grade Invoice Manager with LangChain, LangGraph, RAG, and MCP servers",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(documents.router)
app.include_router(validation.router)
app.include_router(chat.router)
app.include_router(analytics.router)
app.include_router(exports.router)
app.include_router(watcher.router)
app.include_router(db.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Invoice Manager API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db = MongoDB.get_database()
        await db.command("ping")
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
