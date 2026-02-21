import logging
from typing import List, Optional, Dict
from bson import ObjectId

from app.db.mongodb import get_database
from app.db.models import ChatMessage

logger = logging.getLogger(__name__)


class ChatRepository:
    """CRUD operations for chat messages."""

    @staticmethod
    async def create(message: ChatMessage) -> str:
        db = get_database()
        msg_dict = message.model_dump(exclude={"id"})
        result = await db.chat_messages.insert_one(msg_dict)
        return str(result.inserted_id)

    @staticmethod
    async def get_session(session_id: str, limit: int = 50) -> List[ChatMessage]:
        db = get_database()
        cursor = db.chat_messages.find(
            {"session_id": session_id, "document_id": None}
        ).sort("timestamp", 1).limit(limit)
        messages = []
        async for msg in cursor:
            msg["id"] = str(msg.get("_id"))
            messages.append(ChatMessage(**msg))
        return messages

    @staticmethod
    async def get_document_session(session_id: str, document_id: str, limit: int = 50) -> List[ChatMessage]:
        db = get_database()
        cursor = db.chat_messages.find(
            {"session_id": session_id, "document_id": document_id}
        ).sort("timestamp", 1).limit(limit)
        messages = []
        async for msg in cursor:
            msg["id"] = str(msg.get("_id"))
            messages.append(ChatMessage(**msg))
        return messages

    @staticmethod
    async def get_recent_sessions(limit: int = 10) -> List[Dict]:
        db = get_database()
        pipeline = [
            {"$match": {"document_id": None}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$session_id",
                "last_message": {"$first": "$content"},
                "last_timestamp": {"$first": "$timestamp"},
                "message_count": {"$sum": 1}
            }},
            {"$sort": {"last_timestamp": -1}},
            {"$limit": limit}
        ]
        sessions = []
        async for session in db.chat_messages.aggregate(pipeline):
            sessions.append({
                "session_id": session["_id"],
                "last_message": session["last_message"][:100],
                "last_timestamp": session["last_timestamp"].isoformat() if session["last_timestamp"] else None,
                "message_count": session["message_count"]
            })
        return sessions

    @staticmethod
    async def delete_session(session_id: str) -> int:
        db = get_database()
        result = await db.chat_messages.delete_many({"session_id": session_id})
        return result.deleted_count
