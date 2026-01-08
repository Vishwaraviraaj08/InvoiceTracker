// API Types for Invoice Manager

export interface DocumentMetadata {
  vendor: string | null;
  invoice_number: string | null;
  date: string | null;
  total: number | null;
  currency: string | null;
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  validation_status: 'pending' | 'valid' | 'invalid' | 'needs_review';
  upload_timestamp: string;
  metadata: DocumentMetadata;
  raw_text_preview?: string;
  raw_text_length?: number;
  has_file?: boolean;
  forced_valid?: boolean;
  admin_corrections?: Record<string, string>;
}

export interface UploadResponse {
  doc_id: string;
  filename: string;
  status: string;
  message: string;
}

export interface ValidationIssue {
  field: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
}

export interface ValidationResponse {
  document_id: string;
  valid: boolean;
  issues: ValidationIssue[];
  needs_review: boolean;
  review_reason: string | null;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  tool_calls?: ToolCall[];
  sources?: string[];
}

export interface ToolCall {
  tool_name: string;
  args: Record<string, unknown>;
  result: unknown;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  tool_used: string | null;
  sources: string[] | null;
  needs_clarification: boolean;
  clarification_question: string | null;
}

export interface ChatHistoryResponse {
  session_id: string;
  document_id?: string;
  messages: ChatMessage[];
  count: number;
}
