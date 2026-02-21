import logging
from typing import List, Optional
from bson import ObjectId

from app.db.mongodb import get_database
from app.db.models import ValidationResult

logger = logging.getLogger(__name__)


class ValidationRepository:
    """CRUD operations for validation results."""

    @staticmethod
    async def create(result: ValidationResult) -> str:
        db = get_database()
        result_dict = result.model_dump(exclude={"id"})
        insert_result = await db.validations.insert_one(result_dict)
        return str(insert_result.inserted_id)

    @staticmethod
    async def get_by_document(document_id: str) -> Optional[ValidationResult]:
        db = get_database()
        doc = await db.validations.find_one(
            {"document_id": document_id},
            sort=[("validated_at", -1)]
        )
        if doc:
            doc["id"] = str(doc.get("_id"))
            return ValidationResult(**doc)
        return None

    @staticmethod
    async def get_all_by_document(document_id: str) -> List[ValidationResult]:
        db = get_database()
        cursor = db.validations.find({"document_id": document_id}).sort("validated_at", -1)
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.get("_id"))
            results.append(ValidationResult(**doc))
        return results

    @staticmethod
    async def delete_by_document(document_id: str) -> int:
        db = get_database()
        result = await db.validations.delete_many({"document_id": document_id})
        return result.deleted_count
