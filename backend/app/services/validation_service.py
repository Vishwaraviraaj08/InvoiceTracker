import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ValidationService:
    """Interface to the validation MCP server."""

    async def validate_invoice(self, document_id: str) -> Dict[str, Any]:
        """Validate an invoice document."""
        from app.mcp.validation_server import get_validation_server
        validation_server = get_validation_server()
        result = await validation_server.execute_tool("validate_invoice", {"document_id": document_id})

        if result.success:
            data = result.data
            return {
                "success": True,
                "document_id": document_id,
                "valid": data.get("valid", False),
                "issues": data.get("issues", []),
                "needs_review": data.get("needs_review", False),
                "review_reason": data.get("review_reason"),
                "validated_at": data.get("validated_at")
            }
        return {"success": False, "document_id": document_id, "error": result.error}

    async def get_validation_status(self, document_id: str) -> Dict[str, Any]:
        """Get validation status for a document."""
        from app.mcp.validation_server import get_validation_server
        validation_server = get_validation_server()
        result = await validation_server.execute_tool("get_validation_result", {"document_id": document_id})

        if result.success:
            return {"success": True, "validation": result.data}
        return {"success": False, "error": result.error}


_validation_service: ValidationService | None = None


def get_validation_service() -> ValidationService:
    """Get or create validation service instance."""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service
