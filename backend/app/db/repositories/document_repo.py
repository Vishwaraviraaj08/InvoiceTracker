"""
Document Repository
CRUD operations for invoice documents
"""

from datetime import datetime
from typing import Optional, List
from bson import ObjectId

from app.db.mongodb import MongoDB
from app.db.models import DocumentModel, DocumentMetadata


class DocumentRepository:
    """Repository for document operations"""
    
    COLLECTION_NAME = "documents"
    
    @classmethod
    def _get_collection(cls):
        return MongoDB.get_collection(cls.COLLECTION_NAME)
    
    @classmethod
    async def create(cls, document: DocumentModel) -> str:
        """Create a new document and return its ID"""
        doc_dict = document.model_dump(by_alias=True, exclude={"id"})
        result = await cls._get_collection().insert_one(doc_dict)
        return str(result.inserted_id)
    
    @classmethod
    async def get_by_id(cls, doc_id: str) -> Optional[DocumentModel]:
        """Get document by ID"""
        doc = await cls._get_collection().find_one({"_id": ObjectId(doc_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
            return DocumentModel(**doc)
        return None
    
    @classmethod
    async def get_all(cls, limit: int = 100, skip: int = 0) -> List[DocumentModel]:
        """Get all documents with pagination"""
        cursor = cls._get_collection().find().skip(skip).limit(limit).sort("upload_timestamp", -1)
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(DocumentModel(**doc))
        return documents
    
    @classmethod
    async def update_status(cls, doc_id: str, status: str) -> bool:
        """Update document validation status"""
        result = await cls._get_collection().update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"validation_status": status}}
        )
        return result.modified_count > 0
    
    @classmethod
    async def update_metadata(cls, doc_id: str, metadata: DocumentMetadata) -> bool:
        """Update document metadata"""
        result = await cls._get_collection().update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"metadata": metadata.model_dump()}}
        )
        return result.modified_count > 0
    
    @classmethod
    async def update(cls, doc_id: str, update_data: dict) -> bool:
        """Generic update method"""
        result = await cls._get_collection().update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    @classmethod
    async def delete(cls, doc_id: str) -> bool:
        """Delete document by ID"""
        result = await cls._get_collection().delete_one({"_id": ObjectId(doc_id)})
        return result.deleted_count > 0
    
    @classmethod
    async def search_by_filename(cls, query: str) -> List[DocumentModel]:
        """Search documents by filename"""
        cursor = cls._get_collection().find(
            {"filename": {"$regex": query, "$options": "i"}}
        ).limit(20)
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(DocumentModel(**doc))
        return documents

    @classmethod
    async def find_by_filename(cls, filename: str) -> Optional[DocumentModel]:
        """Find document by exact filename"""
        doc = await cls._get_collection().find_one({"filename": filename})
        if doc:
            doc["_id"] = str(doc["_id"])
            return DocumentModel(**doc)
        return None
