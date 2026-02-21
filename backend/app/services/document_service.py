import logging
from typing import Dict, Any, Optional
from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.embedding_repo import EmbeddingRepository
from app.db.repositories.validation_repo import ValidationRepository
from app.db.models import DocumentModel, DocumentMetadata
from app.core.langchain.rag import get_rag_pipeline
from app.utils.text_extraction import extract_text
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentService:
    """Handles document upload, retrieval, validation, and deletion."""

    async def upload_document(self, filename: str, file_content: bytes) -> Dict[str, Any]:
        """Upload and process a document: extract text, store, and index for RAG."""
        try:
            logger.info(f"Processing upload: {filename}")
            text, file_type = extract_text(filename, file_content)

            if not text or text.startswith("["):
                logger.warning(f"Limited text extraction for {filename}")

            document = DocumentModel(
                filename=filename,
                file_type=file_type,
                raw_text=text,
                file_data=file_content,
                metadata=DocumentMetadata(),
                upload_timestamp=datetime.utcnow(),
                validation_status="pending"
            )

            doc_id = await DocumentRepository.create(document)
            logger.info(f"Document stored with ID: {doc_id}")

            rag_pipeline = get_rag_pipeline()
            chunks_indexed = await rag_pipeline.index_document(doc_id, text)
            logger.info(f"Indexed {chunks_indexed} chunks for document {doc_id}")

            return {
                "success": True,
                "document_id": doc_id,
                "filename": filename,
                "file_type": file_type,
                "text_length": len(text),
                "chunks_indexed": chunks_indexed
            }
        except Exception as e:
            logger.error(f"Upload failed for {filename}: {e}")
            raise

    async def get_document_file(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get file data for download."""
        document = await DocumentRepository.get_by_id(document_id)
        if not document or not document.file_data:
            return None
        return {
            "filename": document.filename,
            "file_type": document.file_type,
            "file_data": document.file_data
        }

    async def force_validate(self, document_id: str, corrections: Dict[str, Any], admin_notes: str = "") -> Dict[str, Any]:
        """Force validate a document with admin corrections."""
        document = await DocumentRepository.get_by_id(document_id)
        if not document:
            return {"success": False, "error": "Document not found"}

        update_data = {
            "validation_status": "valid",
            "forced_valid": True,
        }

        metadata_updates = {}
        if "vendor" in corrections:
            metadata_updates["metadata.vendor"] = corrections["vendor"]
        if "invoice_number" in corrections:
            metadata_updates["metadata.invoice_number"] = corrections["invoice_number"]
        if "total" in corrections:
            metadata_updates["metadata.total"] = float(corrections["total"])
        if "date" in corrections:
            metadata_updates["metadata.date"] = corrections["date"]
        if "currency" in corrections:
            metadata_updates["metadata.currency"] = corrections["currency"]

        if admin_notes:
            update_data["admin_notes"] = admin_notes
        if corrections:
            update_data["admin_corrections"] = corrections

        update_data.update(metadata_updates)
        await DocumentRepository.update_status(document_id, update_data)

        return {"success": True, "message": f"Document {document.filename} force validated"}

    async def list_documents(self, limit: int = 50) -> list:
        """List all documents."""
        return await DocumentRepository.get_all(limit=limit)

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and all related data."""
        try:
            await EmbeddingRepository.delete_by_document(document_id)
            await ValidationRepository.delete_by_document(document_id)
            return await DocumentRepository.delete(document_id)
        except Exception as e:
            logger.error(f"Delete failed for {document_id}: {e}")
            return False

    async def get_document(self, document_id: str) -> Optional[DocumentModel]:
        """Get a single document by ID."""
        return await DocumentRepository.get_by_id(document_id)


_document_service: DocumentService | None = None


def get_document_service() -> DocumentService:
    """Get or create document service instance."""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service
