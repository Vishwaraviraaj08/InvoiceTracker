import logging
from typing import List, Optional
from bson import ObjectId
import numpy as np

from app.db.mongodb import get_database
from app.db.models import EmbeddingChunk

logger = logging.getLogger(__name__)


class EmbeddingRepository:
    """CRUD operations for document embeddings."""

    @staticmethod
    async def create(chunk: EmbeddingChunk) -> str:
        db = get_database()
        chunk_dict = chunk.model_dump(exclude={"id"})
        result = await db.embeddings.insert_one(chunk_dict)
        return str(result.inserted_id)

    @staticmethod
    async def create_many(chunks: List[EmbeddingChunk]) -> int:
        if not chunks:
            return 0
        db = get_database()
        chunk_dicts = [c.model_dump(exclude={"id"}) for c in chunks]
        result = await db.embeddings.insert_many(chunk_dicts)
        return len(result.inserted_ids)

    @staticmethod
    async def get_by_document(document_id: str) -> List[EmbeddingChunk]:
        db = get_database()
        cursor = db.embeddings.find({"document_id": document_id}).sort("chunk_index", 1)
        chunks = []
        async for doc in cursor:
            doc["id"] = str(doc.get("_id"))
            chunks.append(EmbeddingChunk(**doc))
        return chunks

    @staticmethod
    async def delete_by_document(document_id: str) -> int:
        db = get_database()
        result = await db.embeddings.delete_many({"document_id": document_id})
        return result.deleted_count

    @staticmethod
    async def similarity_search(
        document_id: str,
        query_embedding: List[float],
        top_k: int = 3
    ) -> List[EmbeddingChunk]:
        """Find most similar chunks using cosine similarity."""
        chunks = await EmbeddingRepository.get_by_document(document_id)
        if not chunks:
            return []

        query_vec = np.array(query_embedding)
        scored_chunks = []

        for chunk in chunks:
            chunk_vec = np.array(chunk.embedding)
            similarity = np.dot(query_vec, chunk_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec) + 1e-10
            )
            scored_chunks.append((chunk, float(similarity)))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in scored_chunks[:top_k]]
