"""
Agent State Definitions
Defines the state that flows through the LangGraph agent
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """State that flows through the LangGraph agent"""
    
    # Input
    user_message: str
    session_id: str
    document_id: Optional[str] = None  # For document-specific queries
    
    # Intent classification
    intent: Optional[Literal[
        "validate_invoice",
        "force_validate",
        "delete_document",
        "export_invoices",
        "query_document",
        "list_documents",
        "get_document_details",
        "general_chat",
        "unclear"
    ]] = None
    
    # Extracted entities
    target_document_id: Optional[str] = None
    query_text: Optional[str] = None
    export_format: Optional[str] = None  # csv or excel
    export_filters: Dict[str, Any] = Field(default_factory=dict)
    
    # Tool execution
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    tool_result: Optional[Dict[str, Any]] = None
    
    # Response
    response: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    download_url: Optional[str] = None  # For export downloads
    
    # Error handling
    error: Optional[str] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    
    # Metadata
    model_used: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class IntentClassification(BaseModel):
    """Result of intent classification"""
    intent: str
    confidence: float
    document_id: Optional[str] = None
    reasoning: str
