"""
Exports API Routes
Handles file downloads for exported data
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/exports", tags=["exports"])

EXPORTS_DIR = Path("./exports")


@router.get("/list")
async def list_exports():
    """List all available export files"""
    if not EXPORTS_DIR.exists():
        return {"exports": []}
    
    files = []
    for f in EXPORTS_DIR.iterdir():
        if f.is_file() and f.suffix in ['.csv', '.xlsx']:
            stat = f.stat()
            files.append({
                "filename": f.name,
                "size": stat.st_size,
                "created": stat.st_ctime,
                "download_url": f"/api/exports/{f.name}"
            })
    
    # Sort by creation time, newest first
    files.sort(key=lambda x: x["created"], reverse=True)
    
    return {"exports": files}


@router.get("/{filename}")
async def download_export(filename: str):
    """Download an exported file"""
    # Security: prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    filepath = EXPORTS_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Export file not found")
    
    # Determine media type
    if filename.endswith('.xlsx'):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = "text/csv"
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type
    )


@router.delete("/{filename}")
async def delete_export(filename: str):
    """Delete an exported file"""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    filepath = EXPORTS_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Export file not found")
    
    os.remove(filepath)
    
    return {"success": True, "message": f"Deleted {filename}"}
