// Documents Page

import { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Card, Button, Modal, Spinner } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { getDocuments, validateInvoice, deleteDocument, forceValidate, renameDocument } from '../services/api';
import { StatusBadge, EmptyState } from '../components/Common';
import PDFViewer from '../components/PDFViewer';
import ForceValidateModal from '../components/ForceValidateModal';
import { RenameModal, DeleteModal } from '../components/ConfirmModals';
import type { Document, ValidationResponse, ValidationIssue } from '../types';

const Documents = () => {
    const navigate = useNavigate();
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [validating, setValidating] = useState<string | null>(null);
    const [validationResult, setValidationResult] = useState<ValidationResponse | null>(null);
    const [showValidation, setShowValidation] = useState(false);

    // PDF Viewer state
    const [showPDF, setShowPDF] = useState(false);
    const [selectedDoc, setSelectedDoc] = useState<{ id: string; filename: string } | null>(null);

    // Force Validate state
    const [showForceValidate, setShowForceValidate] = useState(false);
    const [forceValidateDoc, setForceValidateDoc] = useState<string | null>(null);
    const [forceValidateIssues, setForceValidateIssues] = useState<ValidationIssue[]>([]);

    // Rename Modal state
    const [showRename, setShowRename] = useState(false);
    const [renameDoc, setRenameDoc] = useState<{ id: string; filename: string } | null>(null);

    // Delete Modal state
    const [showDelete, setShowDelete] = useState(false);
    const [deleteDoc, setDeleteDoc] = useState<{ id: string; filename: string } | null>(null);

    // Prevent double fetch in React StrictMode
    const hasFetched = useRef(false);

    useEffect(() => {
        if (hasFetched.current) return;
        hasFetched.current = true;
        loadDocuments();
    }, []);

    const loadDocuments = async () => {
        try {
            const docs = await getDocuments();
            setDocuments(docs);
        } catch (error) {
            console.error('Failed to load documents:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleValidate = async (docId: string) => {
        setValidating(docId);
        try {
            const result = await validateInvoice(docId);
            setValidationResult(result);
            setShowValidation(true);
            // Refresh documents to update status
            loadDocuments();
        } catch (error) {
            console.error('Validation failed:', error);
        } finally {
            setValidating(null);
        }
    };

    // Open delete confirmation modal
    const handleDeleteClick = (docId: string, filename: string) => {
        setDeleteDoc({ id: docId, filename });
        setShowDelete(true);
    };

    // Actual delete action
    const handleDeleteConfirm = async () => {
        if (!deleteDoc) return;
        await deleteDocument(deleteDoc.id);
        setShowDelete(false);
        setDeleteDoc(null);
        loadDocuments();
    };

    const handleOpenPDF = (docId: string, filename: string) => {
        setSelectedDoc({ id: docId, filename });
        setShowPDF(true);
    };

    const handleClosePDF = () => {
        setShowPDF(false);
        setSelectedDoc(null);
    };

    const handleOpenForceValidate = () => {
        if (validationResult) {
            setForceValidateDoc(validationResult.document_id);
            setForceValidateIssues(validationResult.issues);
            setShowValidation(false);
            setShowForceValidate(true);
        }
    };

    const handleForceValidate = async (corrections: Record<string, string>) => {
        if (!forceValidateDoc) return;

        await forceValidate(forceValidateDoc, corrections);
        setShowForceValidate(false);
        setForceValidateDoc(null);
        loadDocuments();
    };

    // Open rename modal
    const handleRenameClick = (docId: string, filename: string) => {
        setRenameDoc({ id: docId, filename });
        setShowRename(true);
    };

    // Actual rename action
    const handleRenameConfirm = async (newName: string) => {
        if (!renameDoc) return;
        await renameDocument(renameDoc.id, newName);
        setShowRename(false);
        setRenameDoc(null);
        loadDocuments();
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    if (loading) {
        return (
            <Container className="py-5 text-center">
                <Spinner animation="border" />
                <p className="mt-3">Loading documents...</p>
            </Container>
        );
    }

    return (
        <Container className="py-4">
            <Row className="mb-4">
                <Col>
                    <h1 className="mb-1">Documents</h1>
                    <p className="text-secondary">All your uploaded invoices</p>
                </Col>
                <Col xs="auto">
                    <Button variant="gradient" className="btn-gradient" onClick={() => navigate('/')}>
                        + Upload New
                    </Button>
                </Col>
            </Row>

            {documents.length === 0 ? (
                <Card className="glass-card">
                    <Card.Body>
                        <EmptyState
                            icon="📄"
                            title="No documents yet"
                            description="Upload your first invoice to get started"
                            action={
                                <Button className="btn-gradient" onClick={() => navigate('/')}>
                                    Upload Invoice
                                </Button>
                            }
                        />
                    </Card.Body>
                </Card>
            ) : (
                <div>
                    {documents.map((doc) => (
                        <div key={doc.id} className="document-item">
                            <div className="d-flex align-items-center gap-3">
                                <div style={{ fontSize: '2rem' }}>
                                    {doc.file_type === 'pdf' ? '📕' : doc.file_type === 'image' ? '🖼️' : '📄'}
                                </div>
                                <div>
                                    <h6
                                        className="mb-1"
                                        style={{ cursor: 'pointer', textDecoration: 'underline' }}
                                        onClick={() => handleOpenPDF(doc.id, doc.filename)}
                                    >
                                        {doc.filename}
                                    </h6>
                                    <div className="d-flex gap-3 text-secondary small">
                                        <span>📅 {formatDate(doc.upload_timestamp)}</span>
                                        {doc.metadata?.vendor && <span>🏢 {doc.metadata.vendor}</span>}
                                        {doc.metadata?.total && (
                                            <span>💰 {doc.metadata.currency || '$'}{doc.metadata.total.toFixed(2)}</span>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="d-flex align-items-center gap-2">
                                <StatusBadge status={doc.validation_status} />

                                <Button
                                    size="sm"
                                    variant="outline-light"
                                    onClick={() => handleValidate(doc.id)}
                                    disabled={validating === doc.id}
                                >
                                    {validating === doc.id ? (
                                        <Spinner animation="border" size="sm" />
                                    ) : (
                                        '✓ Validate'
                                    )}
                                </Button>

                                <Button
                                    size="sm"
                                    variant="outline-info"
                                    onClick={() => navigate(`/chat/${doc.id}`)}
                                >
                                    💬 Chat
                                </Button>

                                <Button
                                    size="sm"
                                    variant="outline-secondary"
                                    onClick={() => handleRenameClick(doc.id, doc.filename)}
                                    title="Rename document"
                                >
                                    ✏️
                                </Button>

                                <Button
                                    size="sm"
                                    variant="outline-danger"
                                    onClick={() => handleDeleteClick(doc.id, doc.filename)}
                                >
                                    🗑️
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* PDF Viewer Modal */}
            {selectedDoc && (
                <PDFViewer
                    show={showPDF}
                    onHide={handleClosePDF}
                    docId={selectedDoc.id}
                    filename={selectedDoc.filename}
                />
            )}

            {/* Validation Result Modal */}
            <Modal show={showValidation} onHide={() => setShowValidation(false)} centered size="lg">
                <Modal.Header closeButton>
                    <Modal.Title>Validation Result</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    {validationResult && (
                        <div>
                            <div className="text-center mb-4">
                                <div style={{ fontSize: '3rem' }}>
                                    {validationResult.valid ? '✅' : '⚠️'}
                                </div>
                                <h5 className={validationResult.valid ? 'text-success' : 'text-warning'}>
                                    {validationResult.valid ? 'Invoice is Valid' : 'Issues Found'}
                                </h5>
                            </div>

                            {validationResult.issues.length > 0 && (
                                <div>
                                    <h6>Issues:</h6>
                                    <ul className="list-unstyled">
                                        {validationResult.issues.map((issue, i) => (
                                            <li key={i} className="mb-2 p-2 rounded" style={{ background: 'rgba(255,255,255,0.05)' }}>
                                                <span className={`badge me-2 ${issue.severity === 'error' ? 'bg-danger' :
                                                    issue.severity === 'warning' ? 'bg-warning text-dark' : 'bg-info'
                                                    }`}>
                                                    {issue.severity}
                                                </span>
                                                <strong>{issue.field}:</strong> {issue.message}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {validationResult.needs_review && (
                                <div className="alert alert-info">
                                    <strong>Manual review recommended:</strong><br />
                                    {validationResult.review_reason || 'Some aspects of this invoice require human verification.'}
                                </div>
                            )}
                        </div>
                    )}
                </Modal.Body>
                <Modal.Footer>
                    {validationResult && !validationResult.valid && (
                        <Button className="btn-gradient" onClick={handleOpenForceValidate}>
                            🔧 Force Validate
                        </Button>
                    )}
                    <Button variant="secondary" onClick={() => setShowValidation(false)}>
                        Close
                    </Button>
                </Modal.Footer>
            </Modal>

            {/* Force Validate Modal */}
            <ForceValidateModal
                show={showForceValidate}
                onHide={() => setShowForceValidate(false)}
                docId={forceValidateDoc || ''}
                issues={forceValidateIssues}
                onForceValidate={handleForceValidate}
            />

            {/* Rename Modal */}
            {renameDoc && (
                <RenameModal
                    show={showRename}
                    onHide={() => { setShowRename(false); setRenameDoc(null); }}
                    currentFilename={renameDoc.filename}
                    onRename={handleRenameConfirm}
                />
            )}

            {/* Delete Confirmation Modal */}
            {deleteDoc && (
                <DeleteModal
                    show={showDelete}
                    onHide={() => { setShowDelete(false); setDeleteDoc(null); }}
                    filename={deleteDoc.filename}
                    onDelete={handleDeleteConfirm}
                />
            )}
        </Container>
    );
};

export default Documents;
