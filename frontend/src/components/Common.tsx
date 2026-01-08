// Common UI Components

import { Spinner } from 'react-bootstrap';

interface StatusBadgeProps {
    status: 'pending' | 'valid' | 'invalid' | 'needs_review';
}

export const StatusBadge = ({ status }: StatusBadgeProps) => {
    const labels: Record<string, string> = {
        pending: 'Pending',
        valid: 'Valid',
        invalid: 'Invalid',
        needs_review: 'Needs Review',
    };

    return (
        <span className={`status-badge status-${status}`}>
            {labels[status] || status}
        </span>
    );
};

interface LoadingOverlayProps {
    message?: string;
}

export const LoadingOverlay = ({ message }: LoadingOverlayProps) => {
    return (
        <div className="spinner-overlay">
            <div className="text-center">
                <Spinner animation="border" variant="light" />
                {message && <p className="mt-3">{message}</p>}
            </div>
        </div>
    );
};

interface ToolStatusProps {
    tool: string;
    isActive: boolean;
}

export const ToolStatus = ({ tool, isActive }: ToolStatusProps) => {
    if (!isActive) return null;

    const toolLabels: Record<string, string> = {
        validate_invoice: '🔍 Validating invoice...',
        query_document: '📄 Querying document...',
        list_invoices: '📋 Listing invoices...',
        get_invoice_details: '📊 Getting details...',
        general_chat: '💬 Processing...',
        rag_query: '🔎 Searching document...',
    };

    return (
        <div className="tool-status">
            <Spinner animation="border" size="sm" />
            <span>{toolLabels[tool] || `Running: ${tool}`}</span>
        </div>
    );
};

interface EmptyStateProps {
    icon: string;
    title: string;
    description: string;
    action?: React.ReactNode;
}

export const EmptyState = ({ icon, title, description, action }: EmptyStateProps) => {
    return (
        <div className="text-center py-5">
            <div className="mb-3" style={{ fontSize: '4rem', opacity: 0.5 }}>{icon}</div>
            <h4>{title}</h4>
            <p className="text-secondary mb-4">{description}</p>
            {action}
        </div>
    );
};
