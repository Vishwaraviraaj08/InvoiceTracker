"""
LangChain Tools
Define tools that can be called by the LangGraph agent
"""

import logging
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool

from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.validation_repo import ValidationRepository

logger = logging.getLogger(__name__)


@tool
async def list_invoices() -> Dict[str, Any]:
    """
    List all uploaded invoices with their validation status.
    Returns a list of invoice documents with id, filename, and status.
    """
    try:
        documents = await DocumentRepository.get_all(limit=50)
        
        return {
            "success": True,
            "count": len(documents),
            "invoices": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "status": doc.validation_status,
                    "uploaded": doc.upload_timestamp.isoformat() if doc.upload_timestamp else None,
                    "vendor": doc.metadata.vendor,
                    "total": doc.metadata.total
                }
                for doc in documents
            ]
        }
    except Exception as e:
        logger.error(f"Error listing invoices: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_invoice_details(document_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific invoice.
    
    Args:
        document_id: The ID of the invoice document
    """
    try:
        document = await DocumentRepository.get_by_id(document_id)
        
        if not document:
            return {"success": False, "error": "Invoice not found"}
        
        validation = await ValidationRepository.get_by_document(document_id)
        
        return {
            "success": True,
            "invoice": {
                "id": document.id,
                "filename": document.filename,
                "file_type": document.file_type,
                "status": document.validation_status,
                "uploaded": document.upload_timestamp.isoformat() if document.upload_timestamp else None,
                "metadata": {
                    "vendor": document.metadata.vendor,
                    "invoice_number": document.metadata.invoice_number,
                    "date": document.metadata.date.isoformat() if document.metadata.date else None,
                    "total": document.metadata.total,
                    "currency": document.metadata.currency
                },
                "validation": {
                    "valid": validation.valid if validation else None,
                    "issues": [i.model_dump() for i in validation.issues] if validation else [],
                    "validated_at": validation.validated_at.isoformat() if validation else None
                } if validation else None
            }
        }
    except Exception as e:
        logger.error(f"Error getting invoice details: {e}")
        return {"success": False, "error": str(e)}


@tool
async def search_invoices(query: str) -> Dict[str, Any]:
    """
    Search invoices by filename.
    
    Args:
        query: Search term to match against invoice filenames
    """
    try:
        documents = await DocumentRepository.search_by_filename(query)
        
        return {
            "success": True,
            "count": len(documents),
            "results": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "status": doc.validation_status
                }
                for doc in documents
            ]
        }
    except Exception as e:
        logger.error(f"Error searching invoices: {e}")
        return {"success": False, "error": str(e)}


# Tool registry for the agent
AVAILABLE_TOOLS = [
    list_invoices,
    get_invoice_details,
    search_invoices
]


def get_tools_description() -> str:
    """Get a formatted description of all available tools"""
    descriptions = []
    for tool in AVAILABLE_TOOLS:
        descriptions.append(f"- {tool.name}: {tool.description}")
    return "\n".join(descriptions)
