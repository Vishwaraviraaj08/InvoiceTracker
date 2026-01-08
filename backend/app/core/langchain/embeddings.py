"""
Embeddings Module
Handles text embedding generation using sentence-transformers
"""

import logging
from typing import List
from functools import lru_cache
from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings using sentence-transformers (runs locally)"""
    
    def __init__(self):
        self.settings = get_settings()
        self._model: SentenceTransformer | None = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the embedding model"""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.settings.embedding_model}")
            self._model = SentenceTransformer(self.settings.embedding_model)
            logger.info("Embedding model loaded successfully")
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return [emb.tolist() for emb in embeddings]
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for embedding.
        
        Args:
            text: The text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Characters of overlap between chunks
        
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at a sentence or word boundary
            if end < len(text):
                # Look for sentence boundaries
                for boundary in ['. ', '.\n', '\n\n', '\n', ' ']:
                    last_boundary = text[start:end].rfind(boundary)
                    if last_boundary > chunk_size // 2:
                        end = start + last_boundary + len(boundary)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
        
        return chunks


# Global instance
_embedding_generator: EmbeddingGenerator | None = None


def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create embedding generator instance"""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator
