"""
Document Routes
API endpoints for document upload and management
"""

import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response

from app.db.models import UploadResponse, DocumentListItem, ForceValidateRequest
from app.services.document_service import get_document_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/upload-invoice", response_model=UploadResponse)
async def upload_invoice(file: UploadFile = File(...)):
    """
    Upload an invoice document (PDF, image, or text).
    
    The document will be:
    1. Text extracted
    2. Stored in database
    3. Indexed for RAG queries
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Read file content
    content = await file.read()
    
    if not content:
        raise HTTPException(status_code=400, detail="Empty file provided")
    
    # Check file size (max 10MB)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
    
    service = get_document_service()
    
    try:
        result = await service.upload_document(file.filename, content)
        return result
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=List[DocumentListItem])
async def list_documents(limit: int = 50, skip: int = 0):
    """
    List all uploaded invoice documents.
    
    Returns documents sorted by upload date (newest first).
    """
    if limit > 100:
        limit = 100
    
    service = get_document_service()
    return await service.list_documents(limit, skip)


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """
    Get a specific document by ID.
    """
    service = get_document_service()
    document = await service.get_document(doc_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "validation_status": document.validation_status,
        "forced_valid": document.forced_valid,
        "admin_corrections": document.admin_corrections,
        "upload_timestamp": document.upload_timestamp.isoformat() if document.upload_timestamp else None,
        "raw_text_preview": document.raw_text[:1000] if document.raw_text else None,
        "raw_text_length": len(document.raw_text) if document.raw_text else 0,
        "has_file": document.file_data is not None,
        "metadata": {
            "vendor": document.metadata.vendor,
            "invoice_number": document.metadata.invoice_number,
            "date": document.metadata.date.isoformat() if document.metadata.date else None,
            "total": document.metadata.total,
            "currency": document.metadata.currency
        }
    }


@router.get("/documents/{doc_id}/file")
async def get_document_file(doc_id: str):
    """
    Get the original file for a document (PDF viewer).
    Returns the file bytes with appropriate content type.
    """
    service = get_document_service()
    file_data = await service.get_file_data(doc_id)
    
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_bytes, filename, file_type = file_data
    
    # Determine content type
    content_types = {
        "pdf": "application/pdf",
        "image": "image/png",  # Default for images
        "text": "text/plain"
    }
    content_type = content_types.get(file_type, "application/octet-stream")
    
    # For images, try to determine specific type
    if file_type == "image":
        if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
            content_type = "image/jpeg"
        elif filename.lower().endswith(".png"):
            content_type = "image/png"
        elif filename.lower().endswith(".gif"):
            content_type = "image/gif"
    
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        }
    )


@router.post("/force-validate/{doc_id}")
async def force_validate_document(doc_id: str, request: ForceValidateRequest):
    """
    Force validate a document with manual corrections.
    
    Use when automatic validation shows errors but admin wants to override.
    """
    service = get_document_service()
    
    success = await service.force_validate(
        doc_id,
        request.corrections,
        request.admin_notes
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "success": True,
        "document_id": doc_id,
        "validation_status": "valid",
        "forced_valid": True,
        "corrections_applied": request.corrections
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document and all associated data.
    """
    service = get_document_service()
    deleted = await service.delete_document(doc_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"deleted": True, "document_id": doc_id}


@router.put("/documents/{doc_id}/rename")
async def rename_document(doc_id: str, new_name: str):
    """
    Rename a document.
    """
    from app.db.repositories.document_repo import DocumentRepository
    
    document = await DocumentRepository.get_by_id(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # If no new name provided, generate default name with timestamp
    if not new_name or new_name.strip() == "":
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Get base name without extension
        base_name = document.filename.rsplit('.', 1)[0] if '.' in document.filename else document.filename
        extension = document.filename.rsplit('.', 1)[1] if '.' in document.filename else ''
        new_name = f"{base_name}_{timestamp}.{extension}" if extension else f"{base_name}_{timestamp}"
    
    await DocumentRepository.update(doc_id, {"filename": new_name})
    
    return {"success": True, "document_id": doc_id, "new_filename": new_name}


@router.get("/documents/{doc_id}/anomalies")
async def check_document_anomalies(doc_id: str):
    """
    Check a document for anomalies (duplicates, unusual prices).
    """
    from app.services.anomaly_detector import get_anomaly_detector
    
    detector = get_anomaly_detector()
    result = await detector.detect_anomalies(doc_id)
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result
