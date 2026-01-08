"""
Chat Repository
CRUD operations for chat messages (global and per-document)
"""

from typing import Optional, List
from bson import ObjectId

from app.db.mongodb import MongoDB
from app.db.models import ChatMessage


class ChatRepository:
    """Repository for chat operations"""
    
    GLOBAL_COLLECTION = "chats_global"
    DOCUMENT_COLLECTION = "chats_per_document"
    
    @classmethod
    def _get_collection(cls, is_global: bool = True):
        collection_name = cls.GLOBAL_COLLECTION if is_global else cls.DOCUMENT_COLLECTION
        return MongoDB.get_collection(collection_name)
    
    @classmethod
    async def create(cls, message: ChatMessage) -> str:
        """Create a new chat message"""
        is_global = message.document_id is None
        doc_dict = message.model_dump(by_alias=True, exclude={"id"})
        result = await cls._get_collection(is_global).insert_one(doc_dict)
        return str(result.inserted_id)
    
    @classmethod
    async def get_session_history(
        cls, 
        session_id: str, 
        document_id: Optional[str] = None,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Get chat history for a session"""
        is_global = document_id is None
        query = {"session_id": session_id}
        
        if not is_global:
            query["document_id"] = document_id
        
        cursor = cls._get_collection(is_global).find(query).sort("timestamp", 1).limit(limit)
        
        messages = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            messages.append(ChatMessage(**doc))
        return messages
    
    @classmethod
    async def get_global_history(cls, session_id: str, limit: int = 50) -> List[ChatMessage]:
        """Get global chat history"""
        return await cls.get_session_history(session_id, None, limit)
    
    @classmethod
    async def get_document_history(
        cls, 
        document_id: str, 
        session_id: str,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Get document-specific chat history"""
        return await cls.get_session_history(session_id, document_id, limit)
    
    @classmethod
    async def get_recent_global_sessions(cls, limit: int = 10) -> List[str]:
        """Get recent global chat session IDs"""
        pipeline = [
            {"$group": {"_id": "$session_id", "last": {"$max": "$timestamp"}}},
            {"$sort": {"last": -1}},
            {"$limit": limit}
        ]
        sessions = []
        async for doc in cls._get_collection(True).aggregate(pipeline):
            sessions.append(doc["_id"])
        return sessions
    
    @classmethod
    async def delete_session(cls, session_id: str, document_id: Optional[str] = None) -> int:
        """Delete all messages in a session"""
        is_global = document_id is None
        query = {"session_id": session_id}
        if not is_global:
            query["document_id"] = document_id
        
        result = await cls._get_collection(is_global).delete_many(query)
        return result.deleted_count
