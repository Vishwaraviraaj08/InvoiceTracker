"""
Invoice Validation MCP Server
Provides tools for validating invoice correctness
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import re

from app.mcp.base import BaseMCPServer, MCPToolDefinition, MCPToolResult
from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.validation_repo import ValidationRepository
from app.db.models import ValidationResult, ValidationIssue, DocumentMetadata
from app.core.llm.groq_client import get_groq_client

logger = logging.getLogger(__name__)


VALIDATION_PROMPT = """You are an expert invoice validator. Analyze the provided invoice text and identify any issues.

Check for:
1. Missing required fields (vendor name, invoice number, date, total amount)
2. Invalid dates (future dates, malformed dates)
3. Suspicious totals (negative amounts, unrealistic values)
4. Missing tax information
5. Inconsistent line item totals
6. Missing contact information
7. Any other anomalies

Invoice text:
{invoice_text}

Respond with a JSON object:
{{
    "valid": true/false,
    "issues": [
        {{"field": "field_name", "severity": "error|warning|info", "message": "description"}}
    ],
    "extracted_metadata": {{
        "vendor": "extracted vendor name or null",
        "invoice_number": "extracted invoice number or null",
        "date": "extracted date as YYYY-MM-DD or null",
        "total": extracted total as number or null,
        "currency": "USD/EUR/etc or null"
    }},
    "needs_manual_review": true/false,
    "review_reason": "reason if manual review needed"
}}"""


class ValidationMCPServer(BaseMCPServer):
    """MCP Server for invoice validation operations"""
    
    def __init__(self):
        super().__init__(
            name="invoice_validation",
            description="Validates invoice documents for correctness and completeness"
        )
        self.groq_client = get_groq_client()
    
    def _register_tools(self) -> None:
        """Register validation tools"""
        
        self.register_tool(MCPToolDefinition(
            name="validate_invoice",
            description="Validate an invoice document for correctness, checking for missing fields, invalid data, and suspicious values",
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The ID of the invoice document to validate"
                    }
                },
                "required": ["document_id"]
            },
            required_params=["document_id"]
        ))
        
        self.register_tool(MCPToolDefinition(
            name="get_validation_rules",
            description="Get the list of validation rules applied to invoices",
            parameters={
                "type": "object",
                "properties": {}
            },
            required_params=[]
        ))
        
        self.register_tool(MCPToolDefinition(
            name="get_validation_result",
            description="Get the latest validation result for a document",
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document ID to get validation result for"
                    }
                },
                "required": ["document_id"]
            },
            required_params=["document_id"]
        ))
        
        self.register_tool(MCPToolDefinition(
            name="force_validate_document",
            description="Force validate a document as valid even if it has issues. Use when admin approves despite errors.",
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document ID to force validate"
                    },
                    "corrections": {
                        "type": "object",
                        "description": "Optional corrections to apply (field: value pairs)"
                    },
                    "admin_notes": {
                        "type": "string",
                        "description": "Optional notes from admin about why force validated"
                    }
                },
                "required": ["document_id"]
            },
            required_params=["document_id"]
        ))
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> MCPToolResult:
        """Execute a validation tool"""
        
        # Validate arguments
        error = self.validate_args(tool_name, args)
        if error:
            return MCPToolResult(success=False, error=error)
        
        try:
            if tool_name == "validate_invoice":
                return await self._validate_invoice(args["document_id"])
            elif tool_name == "get_validation_rules":
                return await self._get_validation_rules()
            elif tool_name == "get_validation_result":
                return await self._get_validation_result(args["document_id"])
            elif tool_name == "force_validate_document":
                return await self._force_validate_document(
                    args["document_id"],
                    args.get("corrections", {}),
                    args.get("admin_notes")
                )
            else:
                return MCPToolResult(success=False, error=f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    async def _validate_invoice(self, document_id: str) -> MCPToolResult:
        """Validate an invoice document"""
        
        # Get document
        document = await DocumentRepository.get_by_id(document_id)
        if not document:
            return MCPToolResult(success=False, error="Document not found")
        
        # Run LLM-based validation
        prompt = VALIDATION_PROMPT.format(invoice_text=document.raw_text[:4000])
        
        result = await self.groq_client.invoke(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are an expert invoice validator. Respond only with valid JSON."
        )
        
        # Parse response
        import json
        response_text = result["content"]
        
        # Extract JSON from possible markdown
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        try:
            validation_data = json.loads(response_text.strip())
        except json.JSONDecodeError:
            # Fallback to basic validation
            validation_data = self._basic_validation(document.raw_text)
        
        # Create validation issues
        issues = [
            ValidationIssue(
                field=issue.get("field", "unknown"),
                severity=issue.get("severity", "warning"),
                message=issue.get("message", "")
            )
            for issue in validation_data.get("issues", [])
        ]
        
        # Store validation result
        validation_result = ValidationResult(
            document_id=document_id,
            valid=validation_data.get("valid", False),
            issues=issues,
            model_used=result["model_used"]
        )
        await ValidationRepository.create(validation_result)
        
        # Update document status
        status = "valid" if validation_data.get("valid") else "invalid"
        if validation_data.get("needs_manual_review"):
            status = "needs_review"
        await DocumentRepository.update_status(document_id, status)
        
        # Update metadata if extracted
        if validation_data.get("extracted_metadata"):
            meta = validation_data["extracted_metadata"]
            metadata = DocumentMetadata(
                vendor=meta.get("vendor"),
                invoice_number=meta.get("invoice_number"),
                date=datetime.fromisoformat(meta["date"]) if meta.get("date") else None,
                total=meta.get("total"),
                currency=meta.get("currency")
            )
            await DocumentRepository.update_metadata(document_id, metadata)
        
        return MCPToolResult(
            success=True,
            data={
                "valid": validation_data.get("valid", False),
                "issues": [i.model_dump() for i in issues],
                "needs_review": validation_data.get("needs_manual_review", False),
                "review_reason": validation_data.get("review_reason")
            },
            metadata={"model_used": result["model_used"]}
        )
    
    def _basic_validation(self, text: str) -> Dict[str, Any]:
        """Fallback basic validation rules"""
        issues = []
        
        # Check for common invoice fields
        if not re.search(r'\b(invoice|inv|bill)\s*#?\s*:?\s*\d+', text, re.IGNORECASE):
            issues.append({
                "field": "invoice_number",
                "severity": "warning",
                "message": "Could not find invoice number"
            })
        
        if not re.search(r'\$?\d+[.,]\d{2}', text):
            issues.append({
                "field": "total",
                "severity": "error",
                "message": "Could not find total amount"
            })
        
        if not re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text):
            issues.append({
                "field": "date",
                "severity": "warning",
                "message": "Could not find invoice date"
            })
        
        return {
            "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
            "needs_manual_review": len(issues) > 0
        }
    
    async def _force_validate_document(
        self, 
        document_id: str, 
        corrections: Dict[str, Any],
        admin_notes: Optional[str] = None
    ) -> MCPToolResult:
        """Force validate a document with optional corrections"""
        
        document = await DocumentRepository.get_by_id(document_id)
        if not document:
            return MCPToolResult(success=False, error="Document not found")
        
        # Update document
        update_data = {
            "validation_status": "valid",
            "forced_valid": True,
            "admin_corrections": corrections or {}
        }
        
        # Apply corrections to metadata if provided
        if corrections:
            if "vendor" in corrections:
                update_data["metadata.vendor"] = corrections["vendor"]
            if "invoice_number" in corrections:
                update_data["metadata.invoice_number"] = corrections["invoice_number"]
            if "total" in corrections:
                try:
                    update_data["metadata.total"] = float(str(corrections["total"]).replace(',', '.'))
                except ValueError:
                    pass
            if "currency" in corrections:
                update_data["metadata.currency"] = corrections["currency"]
        
        await DocumentRepository.update(document_id, update_data)
        
        logger.info(f"Force validated document {document_id} via chat")
        
        return MCPToolResult(
            success=True,
            data={
                "document_id": document_id,
                "validation_status": "valid",
                "forced_valid": True,
                "corrections_applied": corrections or {},
                "admin_notes": admin_notes,
                "message": f"Document '{document.filename}' has been force validated as valid."
            }
        )
    
    async def _get_validation_rules(self) -> MCPToolResult:
        """Get validation rules"""
        return MCPToolResult(
            success=True,
            data={
                "rules": [
                    {"name": "vendor_name", "description": "Invoice must have vendor/seller name", "severity": "error"},
                    {"name": "invoice_number", "description": "Invoice must have unique invoice number", "severity": "error"},
                    {"name": "invoice_date", "description": "Invoice must have valid date", "severity": "error"},
                    {"name": "total_amount", "description": "Invoice must have total amount", "severity": "error"},
                    {"name": "line_items", "description": "Line items should sum to total", "severity": "warning"},
                    {"name": "tax_info", "description": "Tax information should be present", "severity": "info"},
                    {"name": "contact_info", "description": "Contact information recommended", "severity": "info"}
                ]
            }
        )
    
    async def _get_validation_result(self, document_id: str) -> MCPToolResult:
        """Get validation result for a document"""
        result = await ValidationRepository.get_by_document(document_id)
        
        if not result:
            return MCPToolResult(
                success=True,
                data={"validated": False, "message": "Document has not been validated yet"}
            )
        
        return MCPToolResult(
            success=True,
            data={
                "validated": True,
                "valid": result.valid,
                "issues": [i.model_dump() for i in result.issues],
                "validated_at": result.validated_at.isoformat(),
                "model_used": result.model_used
            }
        )


# Global instance
_validation_server: ValidationMCPServer | None = None


def get_validation_server() -> ValidationMCPServer:
    """Get or create validation MCP server instance"""
    global _validation_server
    if _validation_server is None:
        _validation_server = ValidationMCPServer()
    return _validation_server
