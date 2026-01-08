// Force Validate Modal Component

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

    // Initialize corrections from issues
    const handleShow = () => {
        const initialCorrections: Record<string, string> = {};
        issues.forEach(issue => {
            initialCorrections[issue.field] = '';
        });
        setCorrections(initialCorrections);
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
            // Filter out empty corrections
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
            size="lg"
        >
            <Modal.Header closeButton>
                <Modal.Title>🔧 Force Validate Document</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <p className="text-secondary mb-4">
                    Review the issues below and provide corrections. Leave empty to ignore.
                </p>

                {issues.map((issue, index) => (
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
                            placeholder={`Correction for ${issue.field}...`}
                            value={corrections[issue.field] || ''}
                            onChange={(e) => handleCorrectionChange(issue.field, e.target.value)}
                        />
                    </div>
                ))}

                <div className="alert alert-info mt-3">
                    <strong>Note:</strong> Force validating will mark this document as valid
                    with your corrections applied for reporting purposes.
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
