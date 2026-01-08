// Folder Watcher Component with polling and notifications

import { useState, useEffect, useCallback, useRef } from 'react';
import { Card, Button, Form, Spinner, Badge, ListGroup } from 'react-bootstrap';
import { useNotifications } from '../context/NotificationContext';

const API_BASE = 'http://localhost:8000';

interface ProcessedFile {
    filename: string;
    doc_id: string;
    processed_at: string;
}

interface WatcherStatus {
    is_running: boolean;
    watch_path: string | null;
    auto_validate: boolean;
    processed_count: number;
    recent_files: ProcessedFile[];
}

const FolderWatcher = () => {
    const [status, setStatus] = useState<WatcherStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(false);
    const [folderPath, setFolderPath] = useState('./watched_invoices');

    const { showSuccess, showInfo } = useNotifications();

    // Track seen file IDs to detect new uploads
    const seenFileIds = useRef<Set<string>>(new Set());
    const isInitialized = useRef(false);

    const fetchStatusAndScan = useCallback(async () => {
        try {
            // First scan for new files
            if (status?.is_running) {
                await fetch(`${API_BASE}/api/watcher/scan`, { method: 'POST' });
            }

            // Then get status
            const res = await fetch(`${API_BASE}/api/watcher/status`);
            const data: WatcherStatus = await res.json();

            // Detect new files
            if (data.recent_files && data.recent_files.length > 0) {
                data.recent_files.forEach((file) => {
                    if (!seenFileIds.current.has(file.doc_id)) {
                        seenFileIds.current.add(file.doc_id);

                        // Only show notification after initial load
                        if (isInitialized.current) {
                            showSuccess(
                                '📄 New Invoice Processed',
                                `${file.filename} has been automatically uploaded`
                            );
                        }
                    }
                });
            }

            setStatus(data);

            if (data.watch_path) {
                setFolderPath(data.watch_path);
            }
        } catch (error) {
            console.error('Failed to fetch watcher status:', error);
        } finally {
            setLoading(false);
            isInitialized.current = true;
        }
    }, [showSuccess, status?.is_running]);

    // Initial fetch (just status, no scan)
    useEffect(() => {
        const fetchInitialStatus = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/watcher/status`);
                const data: WatcherStatus = await res.json();

                // Initialize seen files
                if (data.recent_files) {
                    data.recent_files.forEach((file) => {
                        seenFileIds.current.add(file.doc_id);
                    });
                }

                setStatus(data);
                if (data.watch_path) {
                    setFolderPath(data.watch_path);
                }
            } catch (error) {
                console.error('Failed to fetch initial status:', error);
            } finally {
                setLoading(false);
                isInitialized.current = true;
            }
        };

        fetchInitialStatus();
    }, []);

    // Poll every 3 seconds when watcher is running
    useEffect(() => {
        if (!status?.is_running) return;

        const interval = setInterval(fetchStatusAndScan, 3000);
        return () => clearInterval(interval);
    }, [status?.is_running, fetchStatusAndScan]);

    const handleStart = async () => {
        setActionLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/watcher/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    folder_path: folderPath,
                    auto_validate: true
                })
            });
            const data = await res.json();
            if (data.success) {
                setStatus(data.status);
                showInfo('📁 Folder Watcher', `Started watching ${folderPath}`);

                // Initialize seen files
                if (data.status.recent_files) {
                    data.status.recent_files.forEach((file: ProcessedFile) => {
                        seenFileIds.current.add(file.doc_id);
                    });
                }
            }
        } catch (error) {
            console.error('Failed to start watcher:', error);
        } finally {
            setActionLoading(false);
        }
    };

    const handleStop = async () => {
        setActionLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/watcher/stop`, {
                method: 'POST'
            });
            const data = await res.json();
            if (data.success) {
                setStatus(data.status);
                showInfo('📁 Folder Watcher', 'Stopped watching folder');
            }
        } catch (error) {
            console.error('Failed to stop watcher:', error);
        } finally {
            setActionLoading(false);
        }
    };

    const handleManualScan = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/watcher/scan`, { method: 'POST' });
            const data = await res.json();
            if (data.new_files > 0) {
                showSuccess('🔍 Scan Complete', `Found ${data.new_files} new file(s)`);
            } else {
                showInfo('🔍 Scan Complete', 'No new files found');
            }
            if (data.status) {
                setStatus(data.status);
            }
        } catch (error) {
            console.error('Scan failed:', error);
        }
    };

    if (loading) {
        return (
            <Card className="glass-card">
                <Card.Body className="text-center py-4">
                    <Spinner animation="border" variant="primary" />
                </Card.Body>
            </Card>
        );
    }

    return (
        <Card className="glass-card">
            <Card.Body>
                <div className="d-flex justify-content-between align-items-center mb-3">
                    <h6 className="mb-0">📁 Auto-Ingestion</h6>
                    <Badge bg={status?.is_running ? 'success' : 'secondary'}>
                        {status?.is_running ? '● Active' : '○ Inactive'}
                    </Badge>
                </div>

                <Form.Group className="mb-3">
                    <Form.Label className="small text-secondary">Watch Folder</Form.Label>
                    <Form.Control
                        type="text"
                        value={folderPath}
                        onChange={(e) => setFolderPath(e.target.value)}
                        placeholder="./watched_invoices"
                        disabled={status?.is_running}
                        className="bg-dark text-white border-secondary"
                        size="sm"
                    />
                </Form.Group>

                <div className="d-grid gap-2 mb-3">
                    {status?.is_running ? (
                        <>
                            <Button
                                variant="outline-info"
                                size="sm"
                                onClick={handleManualScan}
                            >
                                🔍 Scan Now
                            </Button>
                            <Button
                                variant="outline-danger"
                                size="sm"
                                onClick={handleStop}
                                disabled={actionLoading}
                            >
                                {actionLoading ? <Spinner size="sm" /> : '⏹️ Stop'}
                            </Button>
                        </>
                    ) : (
                        <Button
                            className="btn-gradient"
                            size="sm"
                            onClick={handleStart}
                            disabled={actionLoading || !folderPath}
                        >
                            {actionLoading ? <Spinner size="sm" /> : '▶️ Start Watching'}
                        </Button>
                    )}
                </div>

                {status?.is_running && (
                    <div className="text-center text-secondary small mb-2">
                        🔄 Polling every 5 seconds
                    </div>
                )}

                {status?.recent_files && status.recent_files.length > 0 && (
                    <div>
                        <h6 className="small text-secondary mb-2">Recent ({status.processed_count})</h6>
                        <ListGroup variant="flush" className="bg-transparent">
                            {status.recent_files.slice(-4).reverse().map((file, idx) => (
                                <ListGroup.Item
                                    key={idx}
                                    className="bg-transparent border-secondary text-white py-1 px-0"
                                >
                                    <div className="d-flex justify-content-between align-items-center">
                                        <span className="small text-truncate" style={{ maxWidth: '140px' }}>
                                            {file.filename}
                                        </span>
                                        <Badge bg="success" className="small">✓</Badge>
                                    </div>
                                </ListGroup.Item>
                            ))}
                        </ListGroup>
                    </div>
                )}
            </Card.Body>
        </Card>
    );
};

export default FolderWatcher;
