// PDF Viewer Component

import { Modal } from 'react-bootstrap';

interface PDFViewerProps {
    show: boolean;
    onHide: () => void;
    docId: string;
    filename: string;
}

const PDFViewer = ({ show, onHide, docId, filename }: PDFViewerProps) => {
    const fileUrl = `http://localhost:8000/api/documents/${docId}/file`;

    return (
        <Modal
            show={show}
            onHide={onHide}
            size="xl"
            centered
            className="pdf-viewer-modal"
            backdrop={true}
            keyboard={true}
        >
            <Modal.Header closeButton>
                <Modal.Title>📄 {filename}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <iframe
                    src={fileUrl}
                    title={filename}
                    style={{ width: '100%', height: '100%', border: 'none' }}
                />
            </Modal.Body>
        </Modal>
    );
};

export default PDFViewer;
