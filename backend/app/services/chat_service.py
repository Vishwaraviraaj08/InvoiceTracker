import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.db.repositories.chat_repo import ChatRepository
from app.db.models import ChatMessage

logger = logging.getLogger(__name__)


class ChatService:
    """Handles chat interactions for both global and document-specific contexts."""

    async def document_chat(self, message: str, session_id: str, document_id: str) -> Dict[str, Any]:
        """Process a document-specific chat message using RAG."""
        try:
            user_msg = ChatMessage(
                session_id=session_id,
                document_id=document_id,
                role="user",
                content=message,
                timestamp=datetime.utcnow()
            )
            await ChatRepository.create(user_msg)

            from app.mcp.rag_server import get_rag_server
            rag_server = get_rag_server()
            result = await rag_server.execute_tool("query_document", {
                "document_id": document_id,
                "question": message
            })

            if result.success:
                response_text = result.data.get("answer", "No answer available")
                sources = result.data.get("sources", [])
            else:
                response_text = f"Error querying document: {result.error}"
                sources = []

            assistant_msg = ChatMessage(
                session_id=session_id,
                document_id=document_id,
                role="assistant",
                content=response_text,
                timestamp=datetime.utcnow(),
                metadata={
                    "tool_used": "rag_query",
                    "model": result.data.get("model_used") if result.success else None,
                    "sources_count": len(sources)
                }
            )
            await ChatRepository.create(assistant_msg)

            return {
                "response": response_text,
                "sources": sources,
                "model_used": result.data.get("model_used") if result.success else None
            }
        except Exception as e:
            logger.error(f"Document chat failed: {e}")
            raise

    async def get_chat_history(self, session_id: str, document_id: str, limit: int = 50) -> List[Dict]:
        """Get chat history for a document session."""
        messages = await ChatRepository.get_document_session(session_id, document_id, limit)

        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                "metadata": msg.metadata
            }
            for msg in messages
        ]


_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """Get or create chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
