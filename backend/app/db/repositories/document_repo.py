import logging
from typing import List, Optional
from bson import ObjectId

from app.db.mongodb import get_database
from app.db.models import DocumentModel

logger = logging.getLogger(__name__)


class DocumentRepository:
    """CRUD operations for invoice documents."""

    @staticmethod
    async def create(document: DocumentModel) -> str:
        db = get_database()
        doc_dict = document.model_dump(exclude={"id"})
        if isinstance(doc_dict.get("file_data"), bytes):
            from bson.binary import Binary
            doc_dict["file_data"] = Binary(doc_dict["file_data"])

        result = await db.documents.insert_one(doc_dict)
        doc_id = str(result.inserted_id)
        await db.documents.update_one({"_id": result.inserted_id}, {"$set": {"id": doc_id}})
        return doc_id

    @staticmethod
    async def get_by_id(document_id: str) -> Optional[DocumentModel]:
        db = get_database()
        doc = await db.documents.find_one({"id": document_id})
        if doc:
            doc["id"] = str(doc.get("id", doc.get("_id")))
            try:
                return DocumentModel(**doc)
            except Exception as e:
                logger.error(f"Failed to parse document {doc.get('id')}: {e}")
                return None
        return None

    @staticmethod
    async def get_all(limit: int = 50) -> List[DocumentModel]:
        db = get_database()
        cursor = db.documents.find({}, {"file_data": 0}).sort("upload_timestamp", -1).limit(limit)
        documents = []
        async for doc in cursor:
            doc["id"] = str(doc.get("id", doc.get("_id")))
            try:
                documents.append(DocumentModel(**doc))
            except Exception as e:
                logger.warning(f"Skipping document {doc.get('id', doc.get('_id'))}: {e}")
        return documents

    @staticmethod
    async def update_status(document_id: str, update_data: dict) -> bool:
        db = get_database()
        result = await db.documents.update_one({"id": document_id}, {"$set": update_data})
        return result.modified_count > 0

    @staticmethod
    async def update_metadata(document_id: str, metadata: dict) -> bool:
        db = get_database()
        update_fields = {f"metadata.{k}": v for k, v in metadata.items()}
        result = await db.documents.update_one({"id": document_id}, {"$set": update_fields})
        return result.modified_count > 0

    @staticmethod
    async def delete(document_id: str) -> bool:
        db = get_database()
        result = await db.documents.delete_one({"id": document_id})
        return result.deleted_count > 0

    @staticmethod
    async def find_by_filename(filename: str) -> Optional[DocumentModel]:
        db = get_database()
        doc = await db.documents.find_one({"filename": filename})
        if doc:
            doc["id"] = str(doc.get("id", doc.get("_id")))
            return DocumentModel(**doc)
        return None

    @staticmethod
    async def search_by_filename(query: str) -> List[DocumentModel]:
        db = get_database()
        cursor = db.documents.find(
            {"filename": {"$regex": query, "$options": "i"}},
            {"file_data": 0}
        ).limit(20)
        documents = []
        async for doc in cursor:
            doc["id"] = str(doc.get("id", doc.get("_id")))
            documents.append(DocumentModel(**doc))
        return documents
