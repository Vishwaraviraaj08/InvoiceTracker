"""
Document MCP Server
Provides tools for listing and managing documents
"""

import logging
from typing import Any, Dict

from app.mcp.base import BaseMCPServer, MCPToolDefinition, MCPToolResult
from app.db.repositories.document_repo import DocumentRepository

logger = logging.getLogger(__name__)


class DocumentMCPServer(BaseMCPServer):
    """MCP Server for document listing and management"""
    
    def __init__(self):
        super().__init__(
            name="document_listing",
            description="List and manage invoice documents"
        )
    
    def _register_tools(self) -> None:
        """Register document tools"""
        
        self.register_tool(MCPToolDefinition(
            name="list_documents",
            description="List all uploaded invoice documents",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum documents to return (default: 50)"
                    },
                    "skip": {
                        "type": "integer",
                        "description": "Number of documents to skip (for pagination)"
                    }
                }
            },
            required_params=[]
        ))
        
        self.register_tool(MCPToolDefinition(
            name="get_document_metadata",
            description="Get metadata for a specific document",
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document ID"
                    }
                },
                "required": ["document_id"]
            },
            required_params=["document_id"]
        ))
        
        self.register_tool(MCPToolDefinition(
            name="search_documents",
            description="Search documents by filename",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to match against filenames"
                    }
                },
                "required": ["query"]
            },
            required_params=["query"]
        ))
        
        self.register_tool(MCPToolDefinition(
            name="delete_document",
            description="Delete a document and all associated data",
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document ID to delete"
                    }
                },
                "required": ["document_id"]
            },
            required_params=["document_id"]
        ))
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> MCPToolResult:
        """Execute a document tool"""
        
        error = self.validate_args(tool_name, args)
        if error:
            return MCPToolResult(success=False, error=error)
        
        try:
            if tool_name == "list_documents":
                return await self._list_documents(
                    args.get("limit", 50),
                    args.get("skip", 0)
                )
            elif tool_name == "get_document_metadata":
                return await self._get_document_metadata(args["document_id"])
            elif tool_name == "search_documents":
                return await self._search_documents(args["query"])
            elif tool_name == "delete_document":
                return await self._delete_document(args["document_id"])
            else:
                return MCPToolResult(success=False, error=f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"Document tool execution failed: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    async def _list_documents(self, limit: int = 50, skip: int = 0) -> MCPToolResult:
        """List all documents"""
        
        documents = await DocumentRepository.get_all(limit, skip)
        
        return MCPToolResult(
            success=True,
            data={
                "documents": [
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "file_type": doc.file_type,
                        "validation_status": doc.validation_status,
                        "upload_timestamp": doc.upload_timestamp.isoformat() if doc.upload_timestamp else None,
                        "metadata": {
                            "vendor": doc.metadata.vendor,
                            "invoice_number": doc.metadata.invoice_number,
                            "total": doc.metadata.total,
                            "currency": doc.metadata.currency
                        }
                    }
                    for doc in documents
                ],
                "count": len(documents),
                "limit": limit,
                "skip": skip
            }
        )
    
    async def _get_document_metadata(self, document_id: str) -> MCPToolResult:
        """Get document metadata"""
        
        document = await DocumentRepository.get_by_id(document_id)
        if not document:
            return MCPToolResult(success=False, error="Document not found")
        
        return MCPToolResult(
            success=True,
            data={
                "id": document.id,
                "filename": document.filename,
                "file_type": document.file_type,
                "validation_status": document.validation_status,
                "upload_timestamp": document.upload_timestamp.isoformat() if document.upload_timestamp else None,
                "raw_text_preview": document.raw_text[:500] if document.raw_text else None,
                "raw_text_length": len(document.raw_text) if document.raw_text else 0,
                "metadata": {
                    "vendor": document.metadata.vendor,
                    "invoice_number": document.metadata.invoice_number,
                    "date": document.metadata.date.isoformat() if document.metadata.date else None,
                    "total": document.metadata.total,
                    "currency": document.metadata.currency,
                    "line_items": document.metadata.line_items
                }
            }
        )
    
    async def _search_documents(self, query: str) -> MCPToolResult:
        """Search documents"""
        
        documents = await DocumentRepository.search_by_filename(query)
        
        return MCPToolResult(
            success=True,
            data={
                "query": query,
                "results": [
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "validation_status": doc.validation_status
                    }
                    for doc in documents
                ],
                "count": len(documents)
            }
        )
    
    async def _delete_document(self, document_id: str) -> MCPToolResult:
        """Delete a document"""
        from app.db.repositories.embedding_repo import EmbeddingRepository
        from app.db.repositories.validation_repo import ValidationRepository
        from app.db.repositories.chat_repo import ChatRepository
        
        # Delete associated data
        await EmbeddingRepository.delete_by_document(document_id)
        await ValidationRepository.delete_by_document(document_id)
        
        # Delete document
        deleted = await DocumentRepository.delete(document_id)
        
        if not deleted:
            return MCPToolResult(success=False, error="Document not found or already deleted")
        
        return MCPToolResult(
            success=True,
            data={
                "document_id": document_id,
                "deleted": True
            }
        )


# Global instance
_document_server: DocumentMCPServer | None = None


def get_document_server() -> DocumentMCPServer:
    """Get or create document MCP server instance"""
    global _document_server
    if _document_server is None:
        _document_server = DocumentMCPServer()
    return _document_server
