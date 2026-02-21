import logging
import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.mcp.base import BaseMCPServer, MCPToolDefinition, MCPToolResult
from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.validation_repo import ValidationRepository
from app.db.models import ValidationResult, ValidationIssue, DocumentMetadata
from app.core.llm.groq_client import get_groq_client

logger = logging.getLogger(__name__)


VALIDATION_PROMPT = """You are an invoice validator. Your job is to meticulously check the invoice text below and accurately report its status.

IMPORTANT RULES:
- SEARCH THE ENTIRE TEXT CAREFULLY before reporting anything as "missing".
- Accept ALL date formats: "16 June 2025", "06/16/2025", "2025-06-16", "16-06-2025", "June 16, 2025", etc. Convert to YYYY-MM-DD in extracted_metadata.
- If data exists in ANY recognizable form, do NOT report it as missing.
- Ensure you accurately distinguish between critical errors and optional warnings.

Critical fields (MUST be present. Flag as "error" if missing, making the invoice invalid):
1. Vendor/seller name
2. Invoice number (any ID/reference number counts)
3. Date (any format)
4. Total amount

Optional fields (Flag as "warning" or "info" if missing. They do NOT make the invoice invalid):
- Tax information
- Contact information
- Bank account details
- Email address

Invoice text:
{invoice_text}

Respond with a JSON object:
{{
    "valid": true/false (true ONLY IF no "error" severity issues are found),
    "issues": [
        {{"field": "field_name", "severity": "error|warning|info", "message": "description"}}
    ],
    "extracted_metadata": {{
        "vendor": "extracted vendor name or null",
        "invoice_number": "extracted invoice number or null",
        "date": "extracted date converted to YYYY-MM-DD or null",
        "total": extracted total as number or null,
        "currency": "USD/EUR/etc or null"
    }},
    "needs_manual_review": true/false,
    "review_reason": "reason if manual review needed"
}}"""


class ValidationMCPServer(BaseMCPServer):
    """MCP Server for invoice validation operations."""

    def __init__(self):
        super().__init__(name="invoice_validation", description="Validates invoice documents for correctness and completeness")
        self.groq_client = get_groq_client()

    def _register_tools(self) -> None:
        self.register_tool(MCPToolDefinition(
            name="validate_invoice",
            description="Validate an invoice document for correctness",
            parameters={"type": "object", "properties": {"document_id": {"type": "string", "description": "The ID of the invoice document to validate"}}, "required": ["document_id"]},
            required_params=["document_id"]
        ))

        self.register_tool(MCPToolDefinition(
            name="get_validation_rules",
            description="Get the list of validation rules applied to invoices",
            parameters={"type": "object", "properties": {}},
            required_params=[]
        ))

        self.register_tool(MCPToolDefinition(
            name="get_validation_result",
            description="Get the latest validation result for a document",
            parameters={"type": "object", "properties": {"document_id": {"type": "string", "description": "The document ID"}}, "required": ["document_id"]},
            required_params=["document_id"]
        ))

        self.register_tool(MCPToolDefinition(
            name="force_validate_document",
            description="Force validate a document as valid even if it has issues.",
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "The document ID to force validate"},
                    "corrections": {"type": "object", "description": "Optional corrections to apply"},
                    "admin_notes": {"type": "string", "description": "Optional notes from admin"}
                },
                "required": ["document_id"]
            },
            required_params=["document_id"]
        ))

    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> MCPToolResult:
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
                return await self._force_validate_document(args["document_id"], args.get("corrections", {}), args.get("admin_notes"))
            else:
                return MCPToolResult(success=False, error=f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return MCPToolResult(success=False, error=str(e))

    async def _validate_invoice(self, document_id: str) -> MCPToolResult:
        document = await DocumentRepository.get_by_id(document_id)
        if not document:
            return MCPToolResult(success=False, error="Document not found")

        prompt = VALIDATION_PROMPT.format(invoice_text=document.raw_text[:4000])

        result = await self.groq_client.invoke(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a lenient invoice validator. Search the text thoroughly before flagging anything as missing. Accept all date formats. Respond only with valid JSON."
        )

        response_text = result["content"]

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        try:
            validation_data = json.loads(response_text.strip())
        except json.JSONDecodeError:
            validation_data = self._basic_validation(document.raw_text)

        issues = [
            ValidationIssue(field=issue.get("field", "unknown"), severity=issue.get("severity", "warning"), message=issue.get("message", ""))
            for issue in validation_data.get("issues", [])
        ]

        validation_result = ValidationResult(
            document_id=document_id,
            valid=validation_data.get("valid", False),
            issues=issues,
            model_used=result["model_used"]
        )
        await ValidationRepository.create(validation_result)

        status = "valid" if validation_data.get("valid") else "invalid"
        if validation_data.get("needs_manual_review"):
            status = "needs_review"
        await DocumentRepository.update_status(document_id, {"validation_status": status})

        if validation_data.get("extracted_metadata"):
            meta = validation_data["extracted_metadata"]
            update_fields = {}
            if meta.get("vendor"):
                update_fields["vendor"] = meta["vendor"]
            if meta.get("invoice_number"):
                update_fields["invoice_number"] = meta["invoice_number"]
            if meta.get("total"):
                update_fields["total"] = meta["total"]
            if meta.get("currency"):
                update_fields["currency"] = meta["currency"]
            if update_fields:
                await DocumentRepository.update_metadata(document_id, update_fields)

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
        """Fallback basic validation rules — lenient."""
        issues = []

        if not re.search(r'\b(invoice|inv|bill|receipt|order|ref)\s*[#:.]?\s*\d+', text, re.IGNORECASE):
            issues.append({"field": "invoice_number", "severity": "warning", "message": "Could not find invoice/reference number"})

        if not re.search(r'[\$€£]?\s*\d+[.,]\d{2}', text):
            issues.append({"field": "total", "severity": "error", "message": "Could not find total amount"})

        # Accept many date formats: DD/MM/YYYY, DD-MM-YYYY, "16 June 2025", "June 16, 2025", YYYY-MM-DD
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}',
            r'\d{4}-\d{2}-\d{2}',
        ]
        has_date = any(re.search(p, text, re.IGNORECASE) for p in date_patterns)
        if not has_date:
            issues.append({"field": "date", "severity": "warning", "message": "Could not find invoice date"})

        return {
            "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
            "needs_manual_review": len(issues) > 0
        }

    async def _force_validate_document(self, document_id: str, corrections: Dict[str, Any], admin_notes: Optional[str] = None) -> MCPToolResult:
        document = await DocumentRepository.get_by_id(document_id)
        if not document:
            return MCPToolResult(success=False, error="Document not found")

        update_data = {"validation_status": "valid", "forced_valid": True, "admin_corrections": corrections or {}}

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

        await DocumentRepository.update_status(document_id, update_data)

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
        return MCPToolResult(
            success=True,
            data={
                "rules": [
                    {"name": "vendor_name", "description": "Invoice must have vendor/seller name", "severity": "error"},
                    {"name": "invoice_number", "description": "Invoice should have an invoice/reference number", "severity": "warning"},
                    {"name": "invoice_date", "description": "Invoice must have a date (any format accepted)", "severity": "warning"},
                    {"name": "total_amount", "description": "Invoice must have total amount", "severity": "error"},
                    {"name": "line_items", "description": "Line items should sum to total", "severity": "info"},
                    {"name": "tax_info", "description": "Tax information is optional", "severity": "info"},
                    {"name": "contact_info", "description": "Contact information is optional", "severity": "info"}
                ]
            }
        )

    async def _get_validation_result(self, document_id: str) -> MCPToolResult:
        result = await ValidationRepository.get_by_document(document_id)

        if not result:
            return MCPToolResult(success=True, data={"validated": False, "message": "Document has not been validated yet"})

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


_validation_server: ValidationMCPServer | None = None


def get_validation_server() -> ValidationMCPServer:
    """Get or create validation MCP server instance."""
    global _validation_server
    if _validation_server is None:
        _validation_server = ValidationMCPServer()
    return _validation_server
