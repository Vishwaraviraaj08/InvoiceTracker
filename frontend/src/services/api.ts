// API Service for Invoice Manager

import axios from 'axios';
import type {
    Document,
    UploadResponse,
    ValidationResponse,
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse
} from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Document APIs
export const uploadInvoice = async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<UploadResponse>('/upload-invoice', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const getDocuments = async (limit = 50, skip = 0): Promise<Document[]> => {
    const response = await api.get<Document[]>('/documents', {
        params: { limit, skip },
    });
    return response.data;
};

export const getDocument = async (docId: string): Promise<Document> => {
    const response = await api.get<Document>(`/documents/${docId}`);
    return response.data;
};

export const deleteDocument = async (docId: string): Promise<void> => {
    await api.delete(`/documents/${docId}`);
};

// Validation APIs
export const validateInvoice = async (docId: string): Promise<ValidationResponse> => {
    const response = await api.post<ValidationResponse>(`/validate-invoice/${docId}`);
    return response.data;
};

export const getValidationStatus = async (docId: string): Promise<ValidationResponse> => {
    const response = await api.get<ValidationResponse>(`/validation-status/${docId}`);
    return response.data;
};

// Chat APIs
export const sendGlobalMessage = async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/chat/global', request);
    return response.data;
};

export const sendDocumentMessage = async (
    docId: string,
    request: ChatRequest
): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>(`/chat/document/${docId}`, request);
    return response.data;
};

export const getGlobalChatHistory = async (
    sessionId: string,
    limit = 50
): Promise<ChatHistoryResponse> => {
    const response = await api.get<ChatHistoryResponse>('/chats/global', {
        params: { session_id: sessionId, limit },
    });
    return response.data;
};

export const getDocumentChatHistory = async (
    docId: string,
    sessionId: string,
    limit = 50
): Promise<ChatHistoryResponse> => {
    const response = await api.get<ChatHistoryResponse>(`/chats/document/${docId}`, {
        params: { session_id: sessionId, limit },
    });
    return response.data;
};

// Force validation
export const forceValidate = async (
    docId: string,
    corrections: Record<string, string>,
    adminNotes?: string
): Promise<{ success: boolean; document_id: string; validation_status: string }> => {
    const response = await api.post(`/force-validate/${docId}`, {
        corrections,
        admin_notes: adminNotes
    });
    return response.data;
};

// Helper to get document file URL for PDF viewer
export const getDocumentFileUrl = (docId: string): string => {
    return `${API_BASE_URL}/documents/${docId}/file`;
};

// Rename document
export const renameDocument = async (
    docId: string,
    newName: string
): Promise<{ success: boolean; document_id: string; new_filename: string }> => {
    const response = await api.put(`/documents/${docId}/rename`, null, {
        params: { new_name: newName }
    });
    return response.data;
};

export default api;

