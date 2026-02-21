from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(str):
    """Custom type for MongoDB ObjectId serialization."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return str(v)


class DocumentMetadata(BaseModel):
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    total: Optional[float] = None
    currency: str = "USD"
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    tax: Optional[float] = None
    subtotal: Optional[float] = None


class DocumentModel(BaseModel):
    id: Optional[str] = None
    filename: str
    file_type: str
    raw_text: str = ""
    file_data: Optional[bytes] = None
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    validation_status: str = "pending"
    forced_valid: bool = False
    admin_corrections: Optional[Dict[str, Any]] = None
    admin_notes: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class EmbeddingChunk(BaseModel):
    id: Optional[str] = None
    document_id: str
    chunk_index: int
    text: str
    embedding: List[float]

    class Config:
        arbitrary_types_allowed = True


class ChatMessage(BaseModel):
    id: Optional[str] = None
    session_id: str
    document_id: Optional[str] = None
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class ValidationIssue(BaseModel):
    field: str
    severity: str
    message: str


class ValidationResult(BaseModel):
    id: Optional[str] = None
    document_id: str
    valid: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    needs_review: bool = False
    review_reason: Optional[str] = None
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    model_used: Optional[str] = None


class ValidationResponse(BaseModel):
    success: bool
    valid: Optional[bool] = None
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    needs_review: bool = False
    review_reason: Optional[str] = None
    message: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class DocumentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    document_id: str


class UploadResponse(BaseModel):
    success: bool
    document_id: Optional[str] = None
    filename: Optional[str] = None
    file_type: Optional[str] = None
    text_length: Optional[int] = None
    chunks_indexed: Optional[int] = None
    message: Optional[str] = None


class ForceValidateRequest(BaseModel):
    corrections: Dict[str, Any] = Field(default_factory=dict)
    admin_notes: str = ""
