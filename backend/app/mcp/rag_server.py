"""
RAG Query MCP Server
Provides tools for querying invoice documents using RAG
"""

import logging
from typing import Any, Dict

from app.mcp.base import BaseMCPServer, MCPToolDefinition, MCPToolResult
from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.embedding_repo import EmbeddingRepository
from app.core.langchain.rag import get_rag_pipeline

logger = logging.getLogger(__name__)


class RAGMCPServer(BaseMCPServer):
    """MCP Server for RAG-based document querying"""
    
    def __init__(self):
        super().__init__(
            name="rag_query",
            description="Query invoice documents using Retrieval-Augmented Generation"
        )
        self.rag_pipeline = get_rag_pipeline()
    
    def _register_tools(self) -> None:
        """Register RAG tools"""
        
        self.register_tool(MCPToolDefinition(
            name="query_document",
            description="Query a specific invoice document with a natural language question. Answers are sourced only from the document's content.",
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The ID of the document to query"
                    },
                    "question": {
                        "type": "string",
                        "description": "The question to ask about the document"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of relevant chunks to retrieve (default: 3)"
                    }
                },
                "required": ["document_id", "question"]
            },
            required_params=["document_id", "question"]
        ))
        
        self.register_tool(MCPToolDefinition(
            name="get_document_context",
            description="Get the full context/summary of an invoice document",
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The ID of the document"
                    },
                    "max_chunks": {
                        "type": "integer",
                        "description": "Maximum chunks to include (default: 10)"
                    }
                },
                "required": ["document_id"]
            },
            required_params=["document_id"]
        ))
        
        self.register_tool(MCPToolDefinition(
            name="index_document",
            description="Create embeddings for a document to enable RAG queries",
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The ID of the document to index"
                    }
                },
                "required": ["document_id"]
            },
            required_params=["document_id"]
        ))
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> MCPToolResult:
        """Execute a RAG tool"""
        
        error = self.validate_args(tool_name, args)
        if error:
            return MCPToolResult(success=False, error=error)
        
        try:
            if tool_name == "query_document":
                return await self._query_document(
                    args["document_id"],
                    args["question"],
                    args.get("top_k", 3)
                )
            elif tool_name == "get_document_context":
                return await self._get_document_context(
                    args["document_id"],
                    args.get("max_chunks", 10)
                )
            elif tool_name == "index_document":
                return await self._index_document(args["document_id"])
            else:
                return MCPToolResult(success=False, error=f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"RAG tool execution failed: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    async def _query_document(
        self, 
        document_id: str, 
        question: str,
        top_k: int = 3
    ) -> MCPToolResult:
        """Query a document using RAG"""
        
        # Verify document exists
        document = await DocumentRepository.get_by_id(document_id)
        if not document:
            return MCPToolResult(success=False, error="Document not found")
        
        # Check if document is indexed
        embeddings = await EmbeddingRepository.get_by_document(document_id)
        if not embeddings:
            # Auto-index if not indexed
            await self.rag_pipeline.index_document(document_id, document.raw_text)
        
        # Query
        result = await self.rag_pipeline.query(document_id, question, top_k)
        
        return MCPToolResult(
            success=True,
            data={
                "answer": result["answer"],
                "sources": result.get("sources", []),
                "chunks_used": result.get("chunks_used", 0)
            },
            metadata={"model_used": result.get("model_used")}
        )
    
    async def _get_document_context(
        self, 
        document_id: str,
        max_chunks: int = 10
    ) -> MCPToolResult:
        """Get full document context"""
        
        document = await DocumentRepository.get_by_id(document_id)
        if not document:
            return MCPToolResult(success=False, error="Document not found")
        
        context = await self.rag_pipeline.get_document_context(document_id, max_chunks)
        
        return MCPToolResult(
            success=True,
            data={
                "document_id": document_id,
                "filename": document.filename,
                "context": context,
                "raw_text_length": len(document.raw_text)
            }
        )
    
    async def _index_document(self, document_id: str) -> MCPToolResult:
        """Index a document for RAG"""
        
        document = await DocumentRepository.get_by_id(document_id)
        if not document:
            return MCPToolResult(success=False, error="Document not found")
        
        chunks_created = await self.rag_pipeline.index_document(
            document_id, 
            document.raw_text
        )
        
        return MCPToolResult(
            success=True,
            data={
                "document_id": document_id,
                "chunks_created": chunks_created,
                "indexed": True
            }
        )


# Global instance
_rag_server: RAGMCPServer | None = None


def get_rag_server() -> RAGMCPServer:
    """Get or create RAG MCP server instance"""
    global _rag_server
    if _rag_server is None:
        _rag_server = RAGMCPServer()
    return _rag_server
