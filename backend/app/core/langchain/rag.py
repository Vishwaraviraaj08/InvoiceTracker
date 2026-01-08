"""
RAG Pipeline
Retrieval-Augmented Generation for per-invoice querying
"""

import logging
from typing import List, Dict, Any, Optional

from app.db.repositories.embedding_repo import EmbeddingRepository
from app.db.repositories.document_repo import DocumentRepository
from app.db.models import EmbeddingChunk
from app.core.langchain.embeddings import get_embedding_generator
from app.core.llm.groq_client import get_groq_client

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAG pipeline for per-invoice document querying.
    Each invoice has its own embedding corpus to ensure answers
    come strictly from that document's content.
    """
    
    RAG_SYSTEM_PROMPT = """You are an AI assistant specialized in answering questions about invoices.
You MUST answer based ONLY on the provided context from the invoice document.
If the information is not in the context, say "This information is not available in the invoice."
Do NOT make up information. Be precise and cite specific values from the invoice.

Context from the invoice:
{context}

Answer the user's question based solely on this context."""
    
    def __init__(self):
        self.embedding_generator = get_embedding_generator()
        self.groq_client = get_groq_client()
    
    async def index_document(self, document_id: str, text: str) -> int:
        """
        Create embeddings for a document and store them.
        
        Args:
            document_id: The document ID
            text: The full document text
        
        Returns:
            Number of chunks created
        """
        # Delete existing embeddings for this document
        await EmbeddingRepository.delete_by_document(document_id)
        
        # Chunk the text
        chunks = self.embedding_generator.chunk_text(text)
        
        if not chunks:
            logger.warning(f"No chunks generated for document {document_id}")
            return 0
        
        # Generate embeddings
        embeddings = self.embedding_generator.embed_texts(chunks)
        
        # Create embedding chunks
        embedding_chunks = []
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            embedding_chunks.append(EmbeddingChunk(
                document_id=document_id,
                chunk_index=idx,
                chunk_text=chunk_text,
                embedding=embedding
            ))
        
        # Store embeddings
        await EmbeddingRepository.create_many(embedding_chunks)
        
        logger.info(f"Indexed {len(embedding_chunks)} chunks for document {document_id}")
        return len(embedding_chunks)
    
    async def query(
        self, 
        document_id: str, 
        question: str,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Query a specific document using RAG.
        
        Args:
            document_id: The document to query
            question: The user's question
            top_k: Number of chunks to retrieve
        
        Returns:
            Dict with answer, sources, and model info
        """
        # Get document to check for admin corrections
        document = await DocumentRepository.get_by_id(document_id)
        
        # Generate query embedding
        query_embedding = self.embedding_generator.embed_text(question)
        
        # Retrieve relevant chunks
        relevant_chunks = await EmbeddingRepository.similarity_search(
            document_id=document_id,
            query_embedding=query_embedding,
            top_k=top_k
        )
        
        if not relevant_chunks:
            return {
                "answer": "No relevant information found in this invoice. The document may not have been indexed yet.",
                "sources": [],
                "model_used": None
            }
        
        # Build context from chunks
        context = "\n\n---\n\n".join([chunk.chunk_text for chunk in relevant_chunks])
        
        # Add admin corrections context if present
        admin_corrections_context = ""
        if document and document.admin_corrections:
            corrections_list = "\n".join([
                f"- {field}: {value}" 
                for field, value in document.admin_corrections.items()
            ])
            admin_corrections_context = f"""

---

IMPORTANT: Admin Corrections Applied to This Invoice
The following fields were manually corrected by an administrator:
{corrections_list}

When answering questions about these fields, mention BOTH the original value from the document AND the corrected value from the admin. Format: "The [field] in the document is [original], but an admin has corrected it to [corrected value]."
"""
            context += admin_corrections_context
        
        # Create prompt with context
        system_prompt = self.RAG_SYSTEM_PROMPT.format(context=context)
        
        # Query LLM
        result = await self.groq_client.invoke(
            messages=[{"role": "user", "content": question}],
            system_prompt=system_prompt
        )
        
        return {
            "answer": result["content"],
            "sources": [chunk.chunk_text[:100] + "..." for chunk in relevant_chunks],
            "model_used": result["model_used"],
            "chunks_used": len(relevant_chunks),
            "has_admin_corrections": document and document.admin_corrections is not None
        }
    
    async def get_document_context(
        self, 
        document_id: str, 
        max_chunks: int = 10
    ) -> str:
        """Get full context from a document for general queries"""
        chunks = await EmbeddingRepository.get_by_document(document_id)
        
        if not chunks:
            return ""
        
        # Return up to max_chunks
        chunks = sorted(chunks, key=lambda x: x.chunk_index)[:max_chunks]
        return "\n\n".join([chunk.chunk_text for chunk in chunks])


# Global instance
_rag_pipeline: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create RAG pipeline instance"""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
