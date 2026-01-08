"""
Validation Service
Business logic for invoice validation
"""

import logging

from app.db.models import ValidationResponse
from app.mcp.validation_server import get_validation_server

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validation operations"""
    
    def __init__(self):
        self.validation_server = get_validation_server()
    
    async def validate_invoice(self, document_id: str) -> ValidationResponse:
        """
        Validate an invoice document.
        Uses the MCP validation server for processing.
        """
        logger.info(f"Validating invoice: {document_id}")
        
        result = await self.validation_server.execute_tool(
            "validate_invoice",
            {"document_id": document_id}
        )
        
        if not result.success:
            return ValidationResponse(
                document_id=document_id,
                valid=False,
                issues=[],
                needs_review=True,
                review_reason=result.error or "Validation failed"
            )
        
        from app.db.models import ValidationIssue
        
        data = result.data
        issues = [
            ValidationIssue(**issue) if isinstance(issue, dict) else issue
            for issue in data.get("issues", [])
        ]
        
        return ValidationResponse(
            document_id=document_id,
            valid=data.get("valid", False),
            issues=issues,
            needs_review=data.get("needs_review", False),
            review_reason=data.get("review_reason")
        )
    
    async def get_validation_status(self, document_id: str) -> dict:
        """Get validation status for a document"""
        result = await self.validation_server.execute_tool(
            "get_validation_result",
            {"document_id": document_id}
        )
        
        if result.success:
            return result.data
        return {"validated": False, "error": result.error}


# Global instance
_validation_service: ValidationService | None = None


def get_validation_service() -> ValidationService:
    """Get or create validation service instance"""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service
