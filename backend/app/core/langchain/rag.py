import logging
from typing import Dict, Any, List, Optional

from app.core.langchain.embeddings import get_embedding_service
from app.core.llm.groq_client import get_groq_client
from app.db.repositories.embedding_repo import EmbeddingRepository
from app.db.repositories.document_repo import DocumentRepository
from app.db.models import EmbeddingChunk

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """You are a helpful assistant that answers questions about invoice documents.
Use ONLY the provided context to answer questions. If the answer is not in the context, say so.
Be specific and reference actual values from the invoice when possible.

{corrections_context}

Context from the invoice:
{context}"""


class RAGPipeline:
    """RAG pipeline for per-invoice document querying."""

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.groq_client = get_groq_client()

    async def index_document(self, document_id: str, text: str) -> int:
        """Chunk, embed, and store a document for RAG queries."""
        chunks = self.embedding_service.chunk_text(text)

        if not chunks:
            logger.warning(f"No chunks generated for document {document_id}")
            return 0

        embeddings = self.embedding_service.embed_batch(chunks)

        embedding_chunks = [
            EmbeddingChunk(
                document_id=document_id,
                chunk_index=i,
                text=chunk,
                embedding=embedding
            )
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]

        await EmbeddingRepository.create_many(embedding_chunks)
        logger.info(f"Indexed {len(embedding_chunks)} chunks for document {document_id}")
        return len(embedding_chunks)

    async def query(
        self,
        document_id: str,
        question: str,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """Query a document using RAG."""
        question_embedding = self.embedding_service.embed_text(question)

        relevant_chunks = await EmbeddingRepository.similarity_search(
            document_id, question_embedding, top_k
        )

        if not relevant_chunks:
            return {
                "answer": "I couldn't find relevant information in this document to answer your question.",
                "sources": [],
                "chunks_used": 0
            }

        context = "\n\n---\n\n".join([
            f"[Section {chunk.chunk_index + 1}]: {chunk.text}"
            for chunk in relevant_chunks
        ])

        corrections_context = await self._get_corrections_context(document_id)

        system_prompt = RAG_SYSTEM_PROMPT.format(
            context=context,
            corrections_context=corrections_context
        )

        result = await self.groq_client.invoke(
            messages=[{"role": "user", "content": question}],
            system_prompt=system_prompt
        )

        return {
            "answer": result["content"],
            "sources": [chunk.text[:100] for chunk in relevant_chunks],
            "chunks_used": len(relevant_chunks),
            "model_used": result["model_used"]
        }

    async def _get_corrections_context(self, document_id: str) -> str:
        """Get admin corrections context for a document."""
        document = await DocumentRepository.get_by_id(document_id)
        if document and document.admin_corrections:
            corrections = document.admin_corrections
            return (
                "IMPORTANT - Admin corrections to this invoice:\n" +
                "\n".join([f"- {k}: {v}" for k, v in corrections.items()]) +
                "\nUse these corrected values when answering questions."
            )
        return ""

    async def get_document_context(self, document_id: str, max_chunks: int = 10) -> str:
        """Get full document context from stored chunks."""
        chunks = await EmbeddingRepository.get_by_document(document_id)

        if not chunks:
            document = await DocumentRepository.get_by_id(document_id)
            return document.raw_text[:2000] if document else "No context available"

        sorted_chunks = sorted(chunks[:max_chunks], key=lambda c: c.chunk_index)
        return "\n\n".join([chunk.text for chunk in sorted_chunks])


_rag_pipeline: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create RAG pipeline instance."""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
