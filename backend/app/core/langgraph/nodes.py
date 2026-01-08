"""
LangGraph Nodes
Individual processing nodes for the agent graph
"""

import logging
import json
import re
from typing import Dict, Any

from app.core.langgraph.state import AgentState
from app.core.llm.groq_client import get_groq_client
from app.core.langchain.rag import get_rag_pipeline
from app.core.langchain.tools import list_invoices, get_invoice_details, search_invoices
from app.db.repositories.document_repo import DocumentRepository

logger = logging.getLogger(__name__)


INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for an invoice management system.
Classify the user's message into one of these intents:

- validate_invoice: User wants to validate an invoice (check for errors, verify correctness)
- force_validate: User wants to force validate an invoice despite errors (admin override, mark as valid)
- query_document: User is asking a question about a specific invoice's content (e.g., "What is the total?", "Who is the vendor?")
- list_documents: User wants to see a list of their invoices
- get_document_details: User wants details about a specific invoice
- delete_document: User wants to delete an invoice
- export_invoices: User wants to export/download invoices to CSV or Excel (e.g., "Export all invoices", "Download my invoices as Excel")
- general_chat: General conversation or questions not specific to invoice operations
- unclear: The intent is not clear and needs clarification

If the user mentions a specific invoice by ID or name, extract it.
For export requests, extract the format (csv/excel) and any filters (vendor, status, date).

Respond with JSON only:
{{
    "intent": "one of the intents above",
    "document_id": "extracted document ID if any, else null",
    "export_format": "csv or excel if export intent, else null",
    "export_filters": {{"vendor": "vendor name if specified", "status": "status if specified"}},
    "reasoning": "brief explanation"
}}

User message: {message}
Current document context: {document_context}"""


async def classify_intent_node(state: AgentState) -> AgentState:
    """Decision node: Classify user intent"""
    logger.info(f"Classifying intent for: {state.user_message[:50]}...")
    
    message_lower = state.user_message.lower()
    
    # Fast-path: Direct keyword matching for export intent
    # This bypasses LLM since it often misclassifies export requests
    if "export" in message_lower or ("download" in message_lower and "invoice" in message_lower):
        export_format = "excel" if ("excel" in message_lower or "xlsx" in message_lower) else "csv"
        state.intent = "export_invoices"
        state.export_format = export_format
        state.export_filters = {}
        logger.info(f"Fast-path: Detected export intent with format {export_format}")
        return state
    
    groq_client = get_groq_client()
    
    document_context = f"User is viewing document: {state.document_id}" if state.document_id else "No specific document selected"
    
    prompt = INTENT_CLASSIFICATION_PROMPT.format(
        message=state.user_message,
        document_context=document_context
    )
    
    try:
        result = await groq_client.invoke(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a precise intent classifier. Respond only with valid JSON."
        )
        
        # Parse JSON response
        response_text = result["content"]
        
        # Extract JSON if wrapped in markdown
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        # Try to find JSON object in the response
        response_text = response_text.strip()
        
        # Look for JSON object pattern
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        
        try:
            classification = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: Try to extract intent from text
            logger.warning(f"JSON parse failed, attempting fallback. Response: {response_text[:200]}")
            if "list" in state.user_message.lower() and "invoice" in state.user_message.lower():
                classification = {"intent": "list_documents"}
            elif "export" in state.user_message.lower() or "download" in state.user_message.lower():
                export_format = "excel" if "excel" in state.user_message.lower() else "csv"
                classification = {"intent": "export_invoices", "export_format": export_format}
            elif "validate" in state.user_message.lower():
                classification = {"intent": "validate_invoice"}
            elif "delete" in state.user_message.lower():
                classification = {"intent": "delete_document"}
            elif "detail" in state.user_message.lower() or "show" in state.user_message.lower():
                classification = {"intent": "get_document_details"}
            else:
                classification = {"intent": "general_chat"}
        
        state.intent = classification.get("intent", "general_chat")
        state.target_document_id = classification.get("document_id") or state.document_id
        state.export_format = classification.get("export_format")
        state.export_filters = classification.get("export_filters", {})
        state.model_used = result["model_used"]
        
        logger.info(f"Classified intent: {state.intent}")
        
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        state.intent = "general_chat"
        state.error = None  # Don't propagate as error to user
    
    return state


async def validation_node(state: AgentState) -> AgentState:
    """Execute invoice validation"""
    logger.info(f"Validation node for document: {state.target_document_id}")
    
    state.tool_name = "validate_invoice"
    
    if not state.target_document_id:
        state.needs_clarification = True
        state.clarification_question = "Which invoice would you like me to validate? Please provide the invoice ID or filename."
        return state
    
    # Execute validation via MCP server
    from app.mcp.validation_server import get_validation_server
    
    validation_server = get_validation_server()
    result = await validation_server.execute_tool("validate_invoice", {"document_id": state.target_document_id})
    
    if result.success:
        data = result.data
        if data.get("valid"):
            state.response = f"✅ **Invoice is valid!**\n\nNo issues found with this invoice."
        else:
            issues_text = "\n".join([
                f"- [{i['severity']}] **{i['field']}**: {i['message']}"
                for i in data.get("issues", [])
            ])
            state.response = f"⚠️ **Issues found in invoice:**\n\n{issues_text}"
            
            if data.get("needs_review"):
                state.response += f"\n\n**Manual review recommended:** {data.get('review_reason', 'Some aspects need human verification.')}"
    else:
        state.error = result.error
    
    state.tool_args = {"document_id": state.target_document_id}
    
    return state


async def force_validate_node(state: AgentState) -> AgentState:
    """Force validate a document as valid despite issues"""
    logger.info(f"Force validate node for document: {state.target_document_id}")
    
    state.tool_name = "force_validate_document"
    
    if not state.target_document_id:
        state.needs_clarification = True
        state.clarification_question = "Which invoice would you like me to force validate? Please provide the invoice ID."
        return state
    
    from app.mcp.validation_server import get_validation_server
    
    validation_server = get_validation_server()
    
    # Get corrections from state if provided
    corrections = getattr(state, 'corrections', {}) or {}
    
    result = await validation_server.execute_tool("force_validate_document", {
        "document_id": state.target_document_id,
        "corrections": corrections,
        "admin_notes": "Force validated via chat"
    })
    
    if result.success:
        state.response = f"✅ **Invoice force validated!**\n\n{result.data.get('message', 'The invoice has been marked as valid.')}"
    else:
        state.error = result.error
    
    return state


async def delete_document_node(state: AgentState) -> AgentState:
    """Delete a document"""
    logger.info(f"Delete document node for: {state.target_document_id}")
    
    state.tool_name = "delete_document"
    
    if not state.target_document_id:
        state.needs_clarification = True
        state.clarification_question = "Which invoice would you like to delete? Please provide the invoice ID or filename."
        return state
    
    # Get document info first
    document = await DocumentRepository.get_by_id(state.target_document_id)
    if not document:
        state.error = "Document not found"
        return state
    
    filename = document.filename
    
    # Import and use document service for deletion
    from app.services.document_service import get_document_service
    
    doc_service = get_document_service()
    success = await doc_service.delete_document(state.target_document_id)
    
    if success:
        state.response = f"🗑️ **Invoice deleted!**\n\nThe invoice '{filename}' has been permanently deleted."
    else:
        state.error = "Failed to delete document"
    
    return state


async def rag_query_node(state: AgentState) -> AgentState:
    """Execute RAG query on a specific document"""
    logger.info(f"RAG query node for document: {state.target_document_id}")
    
    state.tool_name = "query_document"
    
    doc_id = state.target_document_id or state.document_id
    
    if not doc_id:
        state.needs_clarification = True
        state.clarification_question = "Which invoice are you asking about? Please select an invoice first."
        return state
    
    rag_pipeline = get_rag_pipeline()
    
    try:
        result = await rag_pipeline.query(
            document_id=doc_id,
            question=state.user_message
        )
        
        state.response = result["answer"]
        state.sources = result.get("sources", [])
        state.model_used = result.get("model_used")
        state.tool_result = result
        
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        state.error = str(e)
    
    return state


async def list_documents_node(state: AgentState) -> AgentState:
    """List all documents"""
    logger.info("List documents node")
    
    state.tool_name = "list_invoices"
    
    try:
        result = await list_invoices.ainvoke({})
        state.tool_result = result
        
        if result.get("success"):
            invoices = result.get("invoices", [])
            if invoices:
                invoice_list = "\n".join([
                    f"- **{inv['filename']}** (ID: {inv['id']}) - Status: {inv['status']}"
                    for inv in invoices
                ])
                state.response = f"Here are your uploaded invoices:\n\n{invoice_list}"
            else:
                state.response = "You don't have any invoices uploaded yet. Use the upload feature to add invoices."
        else:
            state.error = result.get("error", "Failed to list invoices")
            
    except Exception as e:
        logger.error(f"List documents failed: {e}")
        state.error = str(e)
    
    return state


async def get_details_node(state: AgentState) -> AgentState:
    """Get invoice details"""
    logger.info(f"Get details node for document: {state.target_document_id}")
    
    state.tool_name = "get_invoice_details"
    
    doc_id = state.target_document_id or state.document_id
    
    if not doc_id:
        state.needs_clarification = True
        state.clarification_question = "Which invoice would you like details about? Please provide the invoice ID or select one."
        return state
    
    try:
        result = await get_invoice_details.ainvoke({"document_id": doc_id})
        state.tool_result = result
        
        if result.get("success"):
            inv = result.get("invoice", {})
            metadata = inv.get("metadata", {})
            
            details = f"""**Invoice Details**

- **Filename:** {inv.get('filename', 'N/A')}
- **Status:** {inv.get('status', 'N/A')}
- **Vendor:** {metadata.get('vendor', 'N/A')}
- **Invoice Number:** {metadata.get('invoice_number', 'N/A')}
- **Date:** {metadata.get('date', 'N/A')}
- **Total:** {metadata.get('currency', '$')}{metadata.get('total', 'N/A')}
"""
            
            if inv.get("validation"):
                validation = inv["validation"]
                details += f"\n**Validation:** {'✓ Valid' if validation.get('valid') else '✗ Invalid'}"
                if validation.get("issues"):
                    details += "\n**Issues:**\n"
                    for issue in validation["issues"]:
                        details += f"- [{issue['severity']}] {issue['field']}: {issue['message']}\n"
            
            state.response = details
        else:
            state.error = result.get("error", "Failed to get invoice details")
            
    except Exception as e:
        logger.error(f"Get details failed: {e}")
        state.error = str(e)
    
    return state


async def general_chat_node(state: AgentState) -> AgentState:
    """Handle general conversation"""
    logger.info("General chat node")
    
    state.tool_name = "general_chat"
    
    groq_client = get_groq_client()
    
    system_prompt = """You are a helpful assistant for an invoice management system.
You can help users with:
- Uploading and managing invoices
- Validating invoice correctness
- Answering questions about specific invoices
- General questions about invoice management

Be helpful, concise, and professional."""
    
    try:
        result = await groq_client.invoke(
            messages=[{"role": "user", "content": state.user_message}],
            system_prompt=system_prompt
        )
        
        state.response = result["content"]
        state.model_used = result["model_used"]
        
    except Exception as e:
        logger.error(f"General chat failed: {e}")
        # Provide a helpful fallback response instead of error
        state.response = """I'm here to help you with invoice management. Here's what I can do:

📤 **Upload Invoices** - Upload PDF invoices for processing
✅ **Validate Invoices** - Check invoices for completeness and accuracy
💬 **Ask Questions** - Query specific invoice details using natural language
📋 **List Invoices** - View all your uploaded invoices
📊 **Export Data** - Export invoices to CSV or Excel

Try asking something like "List all my invoices" or upload a document to get started!"""
        state.error = None  # Don't propagate as error
    
    return state


async def export_invoices_node(state: AgentState) -> AgentState:
    """Export invoices to CSV or Excel"""
    logger.info(f"Export invoices node - Format: {state.export_format}, Filters: {state.export_filters}")
    
    state.tool_name = "export_invoices"
    
    from app.core.tools.export_tool import export_invoices
    
    try:
        # Determine format
        export_format = state.export_format or "csv"
        filters = state.export_filters or {}
        
        # Call export tool
        result = await export_invoices(
            format=export_format,
            vendor=filters.get("vendor"),
            status=filters.get("status"),
            date_range=filters.get("date_range")
        )
        
        if result.get("success"):
            state.download_url = result.get("download_url")
            state.response = f"""📥 **Export Complete!**

I've exported **{result.get('invoice_count', 0)} invoices** to {export_format.upper()} format.

**Download Link:** [Click here to download]({result.get('download_url')})

Filters applied:
{f"- Vendor: {filters.get('vendor')}" if filters.get('vendor') else "- All vendors"}
{f"- Status: {filters.get('status')}" if filters.get('status') else "- All statuses"}
"""
        else:
            state.error = result.get("error", "Export failed")
            state.response = f"❌ Export failed: {state.error}"
            
    except Exception as e:
        logger.error(f"Export failed: {e}")
        state.error = str(e)
        state.response = f"❌ Export failed: {e}"
    
    return state


async def fallback_node(state: AgentState) -> AgentState:
    """Handle errors and unclear requests"""
    logger.info(f"Fallback node - Error: {state.error}, Needs clarification: {state.needs_clarification}")
    
    if state.needs_clarification:
        state.response = state.clarification_question or "I'm not sure what you're asking. Could you please clarify?"
    elif state.error:
        state.response = f"I encountered an issue: {state.error}. Please try again or rephrase your request."
    else:
        state.response = "I'm not sure how to help with that. You can ask me to:\n- List your invoices\n- Validate an invoice\n- Answer questions about a specific invoice\n- Get invoice details"
    
    return state


async def response_node(state: AgentState) -> AgentState:
    """Format final response"""
    logger.info("Response node")
    
    if not state.response:
        if state.error:
            state.response = f"Sorry, something went wrong: {state.error}"
        else:
            state.response = "I processed your request but have no response to show."
    
    return state
