"""
Document Service
Business logic for document upload and management
"""

import logging
from typing import Optional
import base64

from app.db.repositories.document_repo import DocumentRepository
from app.db.models import DocumentModel, DocumentMetadata, UploadResponse, DocumentListItem
from app.utils.text_extraction import extract_text
from app.core.langchain.rag import get_rag_pipeline

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document operations"""
    
    def __init__(self):
        self.rag_pipeline = get_rag_pipeline()
    
    async def upload_document(
        self, 
        filename: str, 
        file_content: bytes
    ) -> UploadResponse:
        """
        Upload and process a new document.
        
        1. Extract text from the document
        2. Store in database (including original file bytes)
        3. Create embeddings for RAG
        """
        logger.info(f"Processing upload: {filename}")
        
        # Extract text
        raw_text, file_type = extract_text(filename, file_content)
        
        if not raw_text or raw_text.startswith("["):
            logger.warning(f"Limited text extraction for {filename}")
        
        # Create document with file bytes
        document = DocumentModel(
            filename=filename,
            file_type=file_type,
            raw_text=raw_text,
            file_data=file_content,  # Store original file
            metadata=DocumentMetadata(),
            validation_status="pending"
        )
        
        # Store in database
        doc_id = await DocumentRepository.create(document)
        logger.info(f"Document created with ID: {doc_id}")
        
        # Index for RAG
        try:
            chunks_created = await self.rag_pipeline.index_document(doc_id, raw_text)
            logger.info(f"Indexed {chunks_created} chunks for document {doc_id}")
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
        
        return UploadResponse(
            doc_id=doc_id,
            filename=filename,
            status="uploaded",
            message=f"Document uploaded successfully. {len(raw_text)} characters extracted."
        )
    
    async def get_document(self, doc_id: str) -> Optional[DocumentModel]:
        """Get a document by ID"""
        return await DocumentRepository.get_by_id(doc_id)
    
    async def get_file_data(self, doc_id: str) -> Optional[tuple[bytes, str, str]]:
        """
        Get file data for a document.
        Returns: (file_bytes, filename, file_type) or None
        """
        document = await DocumentRepository.get_by_id(doc_id)
        if not document or not document.file_data:
            return None
        return (document.file_data, document.filename, document.file_type)
    
    async def force_validate(
        self, 
        doc_id: str, 
        corrections: dict,
        admin_notes: Optional[str] = None
    ) -> bool:
        """
        Force validate a document with manual corrections.
        """
        document = await DocumentRepository.get_by_id(doc_id)
        if not document:
            return False
        
        # Update document
        update_data = {
            "validation_status": "valid",
            "forced_valid": True,
            "admin_corrections": corrections
        }
        
        # Apply corrections to metadata if provided
        if "vendor" in corrections:
            update_data["metadata.vendor"] = corrections["vendor"]
        if "invoice_number" in corrections:
            update_data["metadata.invoice_number"] = corrections["invoice_number"]
        if "total" in corrections:
            try:
                update_data["metadata.total"] = float(corrections["total"])
            except ValueError:
                pass
        
        await DocumentRepository.update(doc_id, update_data)
        logger.info(f"Document {doc_id} force validated with corrections: {corrections}")
        return True
    
    async def list_documents(self, limit: int = 50, skip: int = 0) -> list[DocumentListItem]:
        """List all documents"""
        documents = await DocumentRepository.get_all(limit, skip)
        
        return [
            DocumentListItem(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                validation_status=doc.validation_status,
                upload_timestamp=doc.upload_timestamp,
                metadata=doc.metadata
            )
            for doc in documents
        ]
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document and associated data"""
        from app.db.repositories.embedding_repo import EmbeddingRepository
        from app.db.repositories.validation_repo import ValidationRepository
        
        # Delete embeddings
        await EmbeddingRepository.delete_by_document(doc_id)
        
        # Delete validation results
        await ValidationRepository.delete_by_document(doc_id)
        
        # Delete document
        return await DocumentRepository.delete(doc_id)


# Global instance
_document_service: DocumentService | None = None


def get_document_service() -> DocumentService:
    """Get or create document service instance"""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service

