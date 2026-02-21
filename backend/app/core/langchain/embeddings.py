import logging
from typing import List
from app.config import get_settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Lazy-load the embedding model on first use."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        settings = get_settings()
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model loaded successfully")
    return _model


class EmbeddingService:
    """Handles text embedding generation and chunking."""

    def __init__(self):
        self.settings = get_settings()

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        model = _get_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        model = _get_model()
        embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [e.tolist() for e in embeddings]

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks."""
        if not text or len(text) < chunk_size:
            return [text] if text else []

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size

            if end < len(text):
                break_point = text.rfind('.', start, end)
                if break_point > start + chunk_size // 2:
                    end = break_point + 1

            chunks.append(text[start:end].strip())
            start = end - overlap

        return [c for c in chunks if c]


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
