"""
Chat History MCP Server
Provides tools for managing chat history
"""

import logging
from typing import Any, Dict
import uuid

from app.mcp.base import BaseMCPServer, MCPToolDefinition, MCPToolResult
from app.db.repositories.chat_repo import ChatRepository
from app.db.models import ChatMessage

logger = logging.getLogger(__name__)


class ChatMCPServer(BaseMCPServer):
    """MCP Server for chat history operations"""
    
    def __init__(self):
        super().__init__(
            name="chat_history",
            description="Manage chat history for global and per-document conversations"
        )
    
    def _register_tools(self) -> None:
        """Register chat tools"""
        
        self.register_tool(MCPToolDefinition(
            name="get_chat_history",
            description="Retrieve chat history for a session",
            parameters={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The chat session ID"
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Optional document ID for per-document chat"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum messages to retrieve (default: 50)"
                    }
                },
                "required": ["session_id"]
            },
            required_params=["session_id"]
        ))
        
        self.register_tool(MCPToolDefinition(
            name="save_message",
            description="Save a chat message",
            parameters={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The chat session ID"
                    },
                    "role": {
                        "type": "string",
                        "description": "Message role: user, assistant, or system"
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content"
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Optional document ID for per-document chat"
                    },
                    "tool_calls": {
                        "type": "array",
                        "description": "Optional list of tool calls made"
                    }
                },
                "required": ["session_id", "role", "content"]
            },
            required_params=["session_id", "role", "content"]
        ))
        
        self.register_tool(MCPToolDefinition(
            name="get_recent_sessions",
            description="Get recent chat sessions",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum sessions to retrieve (default: 10)"
                    }
                }
            },
            required_params=[]
        ))
        
        self.register_tool(MCPToolDefinition(
            name="delete_session",
            description="Delete a chat session",
            parameters={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID to delete"
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Optional document ID for per-document chat"
                    }
                },
                "required": ["session_id"]
            },
            required_params=["session_id"]
        ))
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> MCPToolResult:
        """Execute a chat tool"""
        
        error = self.validate_args(tool_name, args)
        if error:
            return MCPToolResult(success=False, error=error)
        
        try:
            if tool_name == "get_chat_history":
                return await self._get_chat_history(
                    args["session_id"],
                    args.get("document_id"),
                    args.get("limit", 50)
                )
            elif tool_name == "save_message":
                return await self._save_message(
                    args["session_id"],
                    args["role"],
                    args["content"],
                    args.get("document_id"),
                    args.get("tool_calls")
                )
            elif tool_name == "get_recent_sessions":
                return await self._get_recent_sessions(args.get("limit", 10))
            elif tool_name == "delete_session":
                return await self._delete_session(
                    args["session_id"],
                    args.get("document_id")
                )
            else:
                return MCPToolResult(success=False, error=f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"Chat tool execution failed: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    async def _get_chat_history(
        self,
        session_id: str,
        document_id: str | None = None,
        limit: int = 50
    ) -> MCPToolResult:
        """Get chat history"""
        
        messages = await ChatRepository.get_session_history(
            session_id, document_id, limit
        )
        
        return MCPToolResult(
            success=True,
            data={
                "session_id": session_id,
                "document_id": document_id,
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
        )
    
    async def _save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        document_id: str | None = None,
        tool_calls: list | None = None
    ) -> MCPToolResult:
        """Save a chat message"""
        
        from app.db.models import ToolCall
        
        tc_models = None
        if tool_calls:
            tc_models = [
                ToolCall(**tc) if isinstance(tc, dict) else tc
                for tc in tool_calls
            ]
        
        message = ChatMessage(
            session_id=session_id,
            document_id=document_id,
            role=role,
            content=content,
            tool_calls=tc_models
        )
        
        message_id = await ChatRepository.create(message)
        
        return MCPToolResult(
            success=True,
            data={
                "message_id": message_id,
                "session_id": session_id
            }
        )
    
    async def _get_recent_sessions(self, limit: int = 10) -> MCPToolResult:
        """Get recent sessions"""
        
        sessions = await ChatRepository.get_recent_global_sessions(limit)
        
        return MCPToolResult(
            success=True,
            data={
                "sessions": sessions,
                "count": len(sessions)
            }
        )
    
    async def _delete_session(
        self,
        session_id: str,
        document_id: str | None = None
    ) -> MCPToolResult:
        """Delete a session"""
        
        deleted_count = await ChatRepository.delete_session(session_id, document_id)
        
        return MCPToolResult(
            success=True,
            data={
                "deleted_count": deleted_count,
                "session_id": session_id
            }
        )


# Global instance
_chat_server: ChatMCPServer | None = None


def get_chat_server() -> ChatMCPServer:
    """Get or create chat MCP server instance"""
    global _chat_server
    if _chat_server is None:
        _chat_server = ChatMCPServer()
    return _chat_server
