"""
Chat Service
Business logic for chat operations including LangGraph orchestration
"""

import logging
import uuid
from typing import Optional

from app.db.models import ChatMessage, ChatRequest, ChatResponse
from app.db.repositories.chat_repo import ChatRepository
from app.core.langgraph.graph import run_agent
from app.mcp.rag_server import get_rag_server
from app.mcp.chat_server import get_chat_server

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat operations"""
    
    def __init__(self):
        self.rag_server = get_rag_server()
        self.chat_server = get_chat_server()
    
    async def global_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Handle global chat using LangGraph agent.
        The agent decides which tool to use based on the message.
        """
        session_id = request.session_id or str(uuid.uuid4())
        
        logger.info(f"Global chat - Session: {session_id}, Message: {request.message[:50]}...")
        
        # Save user message
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=request.message
        )
        await ChatRepository.create(user_message)
        
        # Run agent with error handling
        try:
            agent_state = await run_agent(
                message=request.message,
                session_id=session_id,
                document_id=None
            )
        except Exception as agent_error:
            logger.error(f"Agent execution failed: {agent_error}")
            # Return a fallback response instead of crashing
            return ChatResponse(
                response="I'm sorry, I encountered an error processing your request. Please try again or ask a simpler question.",
                session_id=session_id,
                tool_used=None,
                sources=None,
                needs_clarification=False,
                clarification_question=None
            )
        
        # Save assistant response
        if agent_state.response:
            assistant_message = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=agent_state.response
            )
            await ChatRepository.create(assistant_message)
        
        return ChatResponse(
            response=agent_state.response or "I couldn't process your request.",
            session_id=session_id,
            tool_used=agent_state.tool_name,
            sources=agent_state.sources,
            needs_clarification=agent_state.needs_clarification,
            clarification_question=agent_state.clarification_question
        )
    
    async def document_chat(
        self, 
        document_id: str,
        request: ChatRequest
    ) -> ChatResponse:
        """
        Handle per-document chat using RAG.
        Answers come only from the specific document's content.
        """
        session_id = request.session_id or str(uuid.uuid4())
        
        logger.info(f"Document chat - Doc: {document_id}, Session: {session_id}")
        
        # Save user message
        user_message = ChatMessage(
            session_id=session_id,
            document_id=document_id,
            role="user",
            content=request.message
        )
        await ChatRepository.create(user_message)
        
        # Query document using RAG
        result = await self.rag_server.execute_tool(
            "query_document",
            {
                "document_id": document_id,
                "question": request.message
            }
        )
        
        if result.success:
            response = result.data.get("answer", "No answer found.")
            sources = result.data.get("sources", [])
        else:
            response = f"Error querying document: {result.error}"
            sources = []
        
        # Save assistant response
        assistant_message = ChatMessage(
            session_id=session_id,
            document_id=document_id,
            role="assistant",
            content=response,
            retrieved_chunks=[s[:50] for s in sources]  # Store chunk previews
        )
        await ChatRepository.create(assistant_message)
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            tool_used="rag_query",
            sources=sources
        )
    
    async def get_chat_history(
        self,
        session_id: str,
        document_id: Optional[str] = None,
        limit: int = 50
    ) -> list[ChatMessage]:
        """Get chat history for a session"""
        return await ChatRepository.get_session_history(
            session_id, 
            document_id, 
            limit
        )
    
    async def get_recent_sessions(self, limit: int = 10) -> list[str]:
        """Get recent global chat sessions"""
        return await ChatRepository.get_recent_global_sessions(limit)


# Global instance
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """Get or create chat service instance"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
