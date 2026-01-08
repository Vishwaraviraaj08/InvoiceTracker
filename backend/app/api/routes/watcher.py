"""
Folder Watcher API Routes
Endpoints for controlling the folder watcher
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/watcher", tags=["watcher"])


class WatcherConfig(BaseModel):
    folder_path: str
    auto_validate: bool = True


@router.get("/status")
async def get_watcher_status():
    """Get the current status of the folder watcher"""
    from app.services.folder_watcher import get_folder_watcher
    
    watcher = get_folder_watcher()
    return watcher.get_status()


@router.post("/start")
async def start_watcher(config: WatcherConfig):
    """Start watching a folder for new invoices"""
    from app.services.folder_watcher import get_folder_watcher
    
    watcher = get_folder_watcher()
    
    success = watcher.start(config.folder_path, config.auto_validate)
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to start watching folder: {config.folder_path}"
        )
    
    return {
        "success": True,
        "message": f"Started watching {config.folder_path}",
        "status": watcher.get_status()
    }


@router.post("/stop")
async def stop_watcher():
    """Stop the folder watcher"""
    from app.services.folder_watcher import get_folder_watcher
    
    watcher = get_folder_watcher()
    
    if not watcher.is_running:
        return {"success": True, "message": "Watcher was not running"}
    
    success = watcher.stop()
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop watcher")
    
    return {
        "success": True,
        "message": "Folder watcher stopped",
        "status": watcher.get_status()
    }


@router.get("/processed")
async def get_processed_files():
    """Get list of recently processed files"""
    from app.services.folder_watcher import get_folder_watcher
    
    watcher = get_folder_watcher()
    
    return {
        "processed_files": watcher.processed_files,
        "total_count": len(watcher.processed_files)
    }


@router.post("/scan")
async def scan_folder():
    """Manually scan folder for unprocessed files"""
    from app.services.folder_watcher import get_folder_watcher
    
    watcher = get_folder_watcher()
    
    if not watcher.watch_path:
        return {"success": False, "message": "No folder configured", "new_files": [], "count": 0}
    
    new_files = await watcher.scan_folder_async()
    
    return {
        "success": True,
        "message": f"Scan complete. Found {len(new_files)} new files.",
        "new_files": new_files,
        "count": len(new_files),
        "status": watcher.get_status()
    }


