import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.services.chat_service import get_chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/document/{doc_id}")
async def document_chat(doc_id: str, request: dict):
    """Per-document RAG chat endpoint."""
    message = request.get("message", "").strip()
    session_id = request.get("session_id")

    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    service = get_chat_service()

    try:
        result = await service.document_chat(message, session_id or "default", doc_id)
        return result
    except Exception as e:
        logger.error(f"Document chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/document/{doc_id}")
async def get_document_chat_history(
    doc_id: str,
    session_id: str = Query(..., description="Chat session ID"),
    limit: int = Query(50, le=100)
):
    """Get chat history for a specific document."""
    service = get_chat_service()

    try:
        messages = await service.get_chat_history(session_id, doc_id, limit)
        return {"session_id": session_id, "document_id": doc_id, "messages": messages, "count": len(messages)}
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
