"""
Chat Routes
API endpoints for global and per-document chat
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.db.models import ChatRequest, ChatResponse, ChatMessage
from app.services.chat_service import get_chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/global", response_model=ChatResponse)
async def global_chat(request: ChatRequest):
    """
    Global chatbot endpoint.
    
    Uses LangGraph agent to:
    - Understand user intent
    - Route to appropriate tool (validation, RAG, listing, etc.)
    - Return structured response
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    service = get_chat_service()
    
    try:
        result = await service.global_chat(request)
        return result
    except Exception as e:
        logger.error(f"Global chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/document/{doc_id}", response_model=ChatResponse)
async def document_chat(doc_id: str, request: ChatRequest):
    """
    Per-document RAG chat endpoint.
    
    Answers come ONLY from the specified document's content.
    Great for asking specific questions about an invoice.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    service = get_chat_service()
    
    try:
        result = await service.document_chat(doc_id, request)
        return result
    except Exception as e:
        logger.error(f"Document chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/global")
async def get_global_chat_history(
    session_id: str = Query(..., description="Chat session ID"),
    limit: int = Query(50, le=100)
):
    """
    Get global chat history for a session.
    """
    service = get_chat_service()
    
    try:
        messages = await service.get_chat_history(session_id, None, limit)
        return {
            "session_id": session_id,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "tool_calls": [tc.model_dump() for tc in msg.tool_calls] if msg.tool_calls else None
                }
                for msg in messages
            ],
            "count": len(messages)
        }
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/document/{doc_id}")
async def get_document_chat_history(
    doc_id: str,
    session_id: str = Query(..., description="Chat session ID"),
    limit: int = Query(50, le=100)
):
    """
    Get chat history for a specific document.
    """
    service = get_chat_service()
    
    try:
        messages = await service.get_chat_history(session_id, doc_id, limit)
        return {
            "session_id": session_id,
            "document_id": doc_id,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "sources": msg.retrieved_chunks
                }
                for msg in messages
            ],
            "count": len(messages)
        }
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/sessions")
async def get_recent_sessions(limit: int = Query(10, le=50)):
    """
    Get recent global chat sessions.
    """
    service = get_chat_service()
    
    try:
        sessions = await service.get_recent_sessions(limit)
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        logger.error(f"Failed to get sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
