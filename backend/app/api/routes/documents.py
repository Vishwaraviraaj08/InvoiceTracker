import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response

from app.db.models import ForceValidateRequest
from app.services.document_service import get_document_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/upload-invoice")
async def upload_invoice(file: UploadFile = File(...)):
    """Upload an invoice document (PDF, image, or text)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Empty file provided")

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    service = get_document_service()

    try:
        result = await service.upload_document(file.filename, content)
        return result
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents(limit: int = 50, skip: int = 0):
    """List all uploaded invoice documents."""
    if limit > 100:
        limit = 100

    service = get_document_service()
    documents = await service.list_documents(limit)

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "validation_status": doc.validation_status,
            "forced_valid": doc.forced_valid,
            "upload_timestamp": doc.upload_timestamp.isoformat() if doc.upload_timestamp else None,
            "metadata": {
                "vendor": doc.metadata.vendor,
                "invoice_number": doc.metadata.invoice_number,
                "date": doc.metadata.date.isoformat() if doc.metadata.date else None,
                "total": doc.metadata.total,
                "currency": doc.metadata.currency
            }
        }
        for doc in documents
    ]


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """Get a specific document by ID."""
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
    """Get the original file for a document."""
    service = get_document_service()
    file_data = await service.get_document_file(doc_id)

    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")

    filename = file_data["filename"]
    file_type = file_data["file_type"]
    file_bytes = file_data["file_data"]

    content_types = {
        "pdf": "application/pdf",
        "image": "image/png",
        "text": "text/plain"
    }
    content_type = content_types.get(file_type, "application/octet-stream")

    if file_type == "image":
        if filename.lower().endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif filename.lower().endswith(".gif"):
            content_type = "image/gif"

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )


@router.post("/force-validate/{doc_id}")
async def force_validate_document(doc_id: str, request: ForceValidateRequest):
    """Force validate a document with manual corrections."""
    service = get_document_service()

    result = await service.force_validate(doc_id, request.corrections, request.admin_notes)

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Document not found"))

    return {
        "success": True,
        "document_id": doc_id,
        "validation_status": "valid",
        "forced_valid": True,
        "corrections_applied": request.corrections
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and all associated data."""
    service = get_document_service()
    deleted = await service.delete_document(doc_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"deleted": True, "document_id": doc_id}


@router.put("/documents/{doc_id}/rename")
async def rename_document(doc_id: str, new_name: str):
    """Rename a document."""
    from app.db.repositories.document_repo import DocumentRepository

    document = await DocumentRepository.get_by_id(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not new_name or new_name.strip() == "":
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = document.filename.rsplit('.', 1)[0] if '.' in document.filename else document.filename
        extension = document.filename.rsplit('.', 1)[1] if '.' in document.filename else ''
        new_name = f"{base_name}_{timestamp}.{extension}" if extension else f"{base_name}_{timestamp}"

    await DocumentRepository.update_status(doc_id, {"filename": new_name})

    return {"success": True, "document_id": doc_id, "new_filename": new_name}


@router.get("/documents/{doc_id}/anomalies")
async def check_document_anomalies(doc_id: str):
    """Check a document for anomalies (duplicates, unusual prices)."""
    from app.services.anomaly_detector import get_anomaly_detector

    detector = get_anomaly_detector()
    result = await detector.run_all_checks(doc_id)

    return result
