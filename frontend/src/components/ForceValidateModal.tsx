// Force Validate Modal with PDF Preview Panel

import { useState } from 'react';
import { Modal, Button, Spinner } from 'react-bootstrap';
import type { ValidationIssue } from '../types';

interface ForceValidateModalProps {
    show: boolean;
    onHide: () => void;
    docId: string;
    issues: ValidationIssue[];
    onForceValidate: (corrections: Record<string, string>) => Promise<void>;
}

const ForceValidateModal = ({
    show,
    onHide,
    docId,
    issues,
    onForceValidate
}: ForceValidateModalProps) => {
    const [corrections, setCorrections] = useState<Record<string, string>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showPdfPreview, setShowPdfPreview] = useState(true);

    const pdfUrl = `http://localhost:8000/api/documents/${docId}/file`;

    const handleShow = () => {
        const initialCorrections: Record<string, string> = {};
        (issues || []).forEach(issue => {
            initialCorrections[issue.field] = '';
        });
        setCorrections(initialCorrections);
        setShowPdfPreview(true);
    };

    const handleCorrectionChange = (field: string, value: string) => {
        setCorrections(prev => ({
            ...prev,
            [field]: value
        }));
    };

    const handleSubmit = async () => {
        setIsSubmitting(true);
        try {
            const validCorrections = Object.fromEntries(
                Object.entries(corrections).filter(([_, value]) => value.trim() !== '')
            );
            await onForceValidate(validCorrections);
            onHide();
        } catch (error) {
            console.error('Force validate failed:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Modal
            show={show}
            onHide={onHide}
            onShow={handleShow}
            centered
            className="force-validate-modal"
            dialogClassName="force-validate-dialog"
            size="xl"
        >
            <Modal.Header closeButton>
                <Modal.Title className="d-flex align-items-center gap-2 w-100">
                    <span>🔧 Force Validate Document</span>
                    <Button
                        size="sm"
                        variant={showPdfPreview ? 'outline-info' : 'outline-secondary'}
                        className="ms-auto me-3"
                        onClick={() => setShowPdfPreview(!showPdfPreview)}
                    >
                        {showPdfPreview ? '📄 Hide Preview' : '📄 Show Preview'}
                    </Button>
                </Modal.Title>
            </Modal.Header>
            <Modal.Body className="p-0">
                <div className={`force-validate-layout ${showPdfPreview ? 'with-preview' : 'no-preview'}`}>
                    {/* PDF Preview Panel */}
                    {showPdfPreview && (
                        <div className="fv-pdf-panel">
                            <iframe
                                src={pdfUrl}
                                title="Document Preview"
                                className="fv-pdf-iframe"
                            />
                        </div>
                    )}

                    {/* Corrections Panel */}
                    <div className="fv-corrections-panel">
                        <div className="p-3">
                            <p className="text-secondary mb-3">
                                Review the issues below and provide corrections. Leave empty to ignore.
                            </p>

                            <div className="fv-issues-list">
                                {(issues || []).map((issue, index) => (
                                    <div key={index} className="correction-item">
                                        <div className="d-flex justify-content-between align-items-start mb-2">
                                            <div className="correction-field">{issue.field}</div>
                                            <span className={`badge ${issue.severity === 'error' ? 'bg-danger' :
                                                issue.severity === 'warning' ? 'bg-warning text-dark' : 'bg-info'
                                                }`}>
                                                {issue.severity}
                                            </span>
                                        </div>
                                        <p className="text-secondary small mb-2">{issue.message}</p>
                                        <input
                                            type="text"
                                            className="correction-input"
                                            placeholder={
                                                issue.field.toLowerCase().includes('date')
                                                    ? 'e.g. 16/06/2025 or 16 June 2025'
                                                    : `Correction for ${issue.field}...`
                                            }
                                            value={corrections[issue.field] || ''}
                                            onChange={(e) => handleCorrectionChange(issue.field, e.target.value)}
                                        />
                                    </div>
                                ))}
                            </div>

                            {(!issues || issues.length === 0) && (
                                <div className="text-center text-secondary py-4">
                                    <div style={{ fontSize: '2rem' }}>✅</div>
                                    <p>No issues found to correct.</p>
                                </div>
                            )}

                            <div className="alert alert-info mt-3">
                                <strong>Note:</strong> Force validating will mark this document as valid
                                with your corrections applied for reporting purposes.
                            </div>
                        </div>
                    </div>
                </div>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide} disabled={isSubmitting}>
                    Cancel
                </Button>
                <Button
                    className="btn-gradient"
                    onClick={handleSubmit}
                    disabled={isSubmitting}
                >
                    {isSubmitting ? (
                        <>
                            <Spinner animation="border" size="sm" className="me-2" />
                            Validating...
                        </>
                    ) : (
                        '✓ Force Validate'
                    )}
                </Button>
            </Modal.Footer>
        </Modal>
    );
};

export default ForceValidateModal;
