"""
Database Models
Pydantic models for MongoDB documents with validation
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(str):
    """Custom ObjectId type for Pydantic"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v, info=None):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        raise ValueError("Invalid ObjectId")


class DocumentMetadata(BaseModel):
    """Extracted metadata from invoice"""
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[datetime] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    line_items: Optional[List[dict]] = None


class DocumentModel(BaseModel):
    """Invoice document model"""
    id: Optional[str] = Field(default=None, alias="_id")
    filename: str
    file_type: str  # pdf, image, text
    raw_text: str
    file_data: Optional[bytes] = None  # Original file bytes for PDF viewing
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    validation_status: str = "pending"  # pending, valid, invalid, needs_review
    forced_valid: bool = False  # True if manually validated by admin
    admin_corrections: Optional[dict] = None  # User-provided corrections
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class EmbeddingChunk(BaseModel):
    """Document embedding chunk"""
    id: Optional[str] = Field(default=None, alias="_id")
    document_id: str
    chunk_index: int
    chunk_text: str
    embedding: List[float]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class ToolCall(BaseModel):
    """Tool call information for chat messages"""
    tool_name: str
    args: dict = {}
    result: Optional[Any] = None


class ChatMessage(BaseModel):
    """Chat message model"""
    id: Optional[str] = Field(default=None, alias="_id")
    session_id: str
    document_id: Optional[str] = None  # None for global chat
    role: str  # user, assistant, system
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    retrieved_chunks: Optional[List[str]] = None  # For RAG queries
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class ValidationIssue(BaseModel):
    """Single validation issue"""
    field: str
    severity: str  # error, warning, info
    message: str


class ValidationResult(BaseModel):
    """Validation result model"""
    id: Optional[str] = Field(default=None, alias="_id")
    document_id: str
    valid: bool
    issues: List[ValidationIssue] = []
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    model_used: str
    
    class Config:
        populate_by_name = True


# Request/Response Models for API

class UploadResponse(BaseModel):
    """Response for document upload"""
    doc_id: str
    filename: str
    status: str
    message: str


class DocumentListItem(BaseModel):
    """Document list item"""
    id: str
    filename: str
    file_type: str
    validation_status: str
    upload_timestamp: datetime
    metadata: DocumentMetadata


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    session_id: str
    tool_used: Optional[str] = None
    sources: Optional[List[str]] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


class ValidationResponse(BaseModel):
    """Validation response model"""
    document_id: str
    valid: bool
    issues: List[ValidationIssue]
    needs_review: bool = False
    review_reason: Optional[str] = None
    suggested_corrections: Optional[List[dict]] = None


class SuggestedCorrection(BaseModel):
    """AI-suggested correction for an issue"""
    field: str
    current_value: Optional[str] = None
    suggested_value: str
    reason: str


class ForceValidateRequest(BaseModel):
    """Request for force validation with manual corrections"""
    corrections: dict  # field: corrected_value pairs
    admin_notes: Optional[str] = None


class EditPDFRequest(BaseModel):
    """Request to edit PDF content"""
    field: str
    old_value: str
    new_value: str
