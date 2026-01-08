// Custom Confirmation Modals

import { useState } from 'react';
import { Modal, Button, Form, Spinner } from 'react-bootstrap';

// Rename Modal
interface RenameModalProps {
    show: boolean;
    onHide: () => void;
    currentFilename: string;
    onRename: (newName: string) => Promise<void>;
}

export const RenameModal = ({ show, onHide, currentFilename, onRename }: RenameModalProps) => {
    const [newName, setNewName] = useState(currentFilename);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async () => {
        if (!newName.trim() || newName === currentFilename) {
            onHide();
            return;
        }

        setIsSubmitting(true);
        try {
            await onRename(newName.trim());
            onHide();
        } catch (error) {
            console.error('Rename failed:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleShow = () => {
        setNewName(currentFilename);
    };

    return (
        <Modal show={show} onHide={onHide} onShow={handleShow} centered>
            <Modal.Header closeButton>
                <Modal.Title>✏️ Rename Document</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form.Group>
                    <Form.Label>New filename</Form.Label>
                    <Form.Control
                        type="text"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        placeholder="Enter new filename..."
                        autoFocus
                    />
                </Form.Group>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide} disabled={isSubmitting}>
                    Cancel
                </Button>
                <Button className="btn-gradient" onClick={handleSubmit} disabled={isSubmitting}>
                    {isSubmitting ? (
                        <>
                            <Spinner animation="border" size="sm" className="me-2" />
                            Renaming...
                        </>
                    ) : (
                        'Rename'
                    )}
                </Button>
            </Modal.Footer>
        </Modal>
    );
};

// Delete Confirmation Modal
interface DeleteModalProps {
    show: boolean;
    onHide: () => void;
    filename: string;
    onDelete: () => Promise<void>;
}

export const DeleteModal = ({ show, onHide, filename, onDelete }: DeleteModalProps) => {
    const [isDeleting, setIsDeleting] = useState(false);

    const handleDelete = async () => {
        setIsDeleting(true);
        try {
            await onDelete();
            onHide();
        } catch (error) {
            console.error('Delete failed:', error);
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <Modal show={show} onHide={onHide} centered>
            <Modal.Header closeButton>
                <Modal.Title>🗑️ Delete Document</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <p>Are you sure you want to delete this document?</p>
                <p className="fw-bold text-warning">"{filename}"</p>
                <div className="alert alert-danger">
                    <strong>Warning:</strong> This action cannot be undone. All associated data including chat history and validation results will be permanently deleted.
                </div>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide} disabled={isDeleting}>
                    Cancel
                </Button>
                <Button variant="danger" onClick={handleDelete} disabled={isDeleting}>
                    {isDeleting ? (
                        <>
                            <Spinner animation="border" size="sm" className="me-2" />
                            Deleting...
                        </>
                    ) : (
                        'Delete Permanently'
                    )}
                </Button>
            </Modal.Footer>
        </Modal>
    );
};
