"""
Embedding Repository
CRUD operations for document embeddings
"""

from typing import Optional, List
from bson import ObjectId
import numpy as np

from app.db.mongodb import MongoDB
from app.db.models import EmbeddingChunk


class EmbeddingRepository:
    """Repository for embedding operations"""
    
    COLLECTION_NAME = "document_embeddings"
    
    @classmethod
    def _get_collection(cls):
        return MongoDB.get_collection(cls.COLLECTION_NAME)
    
    @classmethod
    async def create(cls, embedding: EmbeddingChunk) -> str:
        """Create a new embedding chunk"""
        doc_dict = embedding.model_dump(by_alias=True, exclude={"id"})
        result = await cls._get_collection().insert_one(doc_dict)
        return str(result.inserted_id)
    
    @classmethod
    async def create_many(cls, embeddings: List[EmbeddingChunk]) -> List[str]:
        """Create multiple embedding chunks"""
        if not embeddings:
            return []
        docs = [e.model_dump(by_alias=True, exclude={"id"}) for e in embeddings]
        result = await cls._get_collection().insert_many(docs)
        return [str(id) for id in result.inserted_ids]
    
    @classmethod
    async def get_by_document(cls, document_id: str) -> List[EmbeddingChunk]:
        """Get all embeddings for a document"""
        cursor = cls._get_collection().find(
            {"document_id": document_id}
        ).sort("chunk_index", 1)
        
        embeddings = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            embeddings.append(EmbeddingChunk(**doc))
        return embeddings
    
    @classmethod
    async def delete_by_document(cls, document_id: str) -> int:
        """Delete all embeddings for a document"""
        result = await cls._get_collection().delete_many({"document_id": document_id})
        return result.deleted_count
    
    @classmethod
    async def similarity_search(
        cls, 
        document_id: str, 
        query_embedding: List[float], 
        top_k: int = 5
    ) -> List[EmbeddingChunk]:
        """
        Find most similar chunks for a document using cosine similarity.
        Note: For production, consider using MongoDB Atlas Vector Search
        """
        embeddings = await cls.get_by_document(document_id)
        
        if not embeddings:
            return []
        
        # Convert to numpy for efficient computation
        query_vec = np.array(query_embedding)
        
        # Calculate cosine similarities
        similarities = []
        for emb in embeddings:
            emb_vec = np.array(emb.embedding)
            similarity = np.dot(query_vec, emb_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(emb_vec) + 1e-8
            )
            similarities.append((similarity, emb))
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [emb for _, emb in similarities[:top_k]]
