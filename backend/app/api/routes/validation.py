"""
Validation Routes
API endpoints for invoice validation
"""

import logging
from fastapi import APIRouter, HTTPException

from app.db.models import ValidationResponse
from app.services.validation_service import get_validation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["validation"])


@router.post("/validate-invoice/{doc_id}", response_model=ValidationResponse)
async def validate_invoice(doc_id: str):
    """
    Validate an invoice document.
    
    Uses LLM to check for:
    - Missing required fields
    - Invalid dates
    - Suspicious totals
    - Inconsistent line items
    
    Returns validation status and any issues found.
    """
    service = get_validation_service()
    
    try:
        result = await service.validate_invoice(doc_id)
        return result
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validation-status/{doc_id}")
async def get_validation_status(doc_id: str):
    """
    Get the validation status for a document.
    """
    service = get_validation_service()
    
    try:
        result = await service.get_validation_status(doc_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get validation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validation-rules")
async def get_validation_rules():
    """
    Get the list of validation rules applied to invoices.
    """
    from app.mcp.validation_server import get_validation_server
    
    server = get_validation_server()
    result = await server.execute_tool("get_validation_rules", {})
    
    if result.success:
        return result.data
    raise HTTPException(status_code=500, detail=result.error)
