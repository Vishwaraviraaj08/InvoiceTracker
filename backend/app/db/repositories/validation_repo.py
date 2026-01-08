"""
Validation Repository
CRUD operations for validation results
"""

from typing import Optional, List
from bson import ObjectId

from app.db.mongodb import MongoDB
from app.db.models import ValidationResult


class ValidationRepository:
    """Repository for validation results"""
    
    COLLECTION_NAME = "validation_results"
    
    @classmethod
    def _get_collection(cls):
        return MongoDB.get_collection(cls.COLLECTION_NAME)
    
    @classmethod
    async def create(cls, validation: ValidationResult) -> str:
        """Create a new validation result"""
        doc_dict = validation.model_dump(by_alias=True, exclude={"id"})
        result = await cls._get_collection().insert_one(doc_dict)
        return str(result.inserted_id)
    
    @classmethod
    async def get_by_document(cls, document_id: str) -> Optional[ValidationResult]:
        """Get latest validation result for a document"""
        doc = await cls._get_collection().find_one(
            {"document_id": document_id},
            sort=[("validated_at", -1)]
        )
        if doc:
            doc["_id"] = str(doc["_id"])
            return ValidationResult(**doc)
        return None
    
    @classmethod
    async def get_all_by_document(cls, document_id: str) -> List[ValidationResult]:
        """Get all validation results for a document"""
        cursor = cls._get_collection().find(
            {"document_id": document_id}
        ).sort("validated_at", -1)
        
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(ValidationResult(**doc))
        return results
    
    @classmethod
    async def delete_by_document(cls, document_id: str) -> int:
        """Delete all validation results for a document"""
        result = await cls._get_collection().delete_many({"document_id": document_id})
        return result.deleted_count
