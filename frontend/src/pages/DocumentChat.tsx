// Document Chat Page (RAG-based)

import { useState, useEffect, useCallback } from 'react';
import { Container, Row, Col, Card, Spinner } from 'react-bootstrap';
import { useParams, useNavigate } from 'react-router-dom';
import { ChatWindow, ChatInput } from '../components/Chat';
import { VoiceButton } from '../components/VoiceButton';
import { VoiceAnimation } from '../components/VoiceAnimation';
import { VoiceRecordingAnimation } from '../components/VoiceRecordingAnimation';
import { sendDocumentMessage, getDocument } from '../services/api';
import { getTTSService } from '../utils/tts';
import { StatusBadge } from '../components/Common';
import type { ChatMessage, Document } from '../types';

const DocumentChat = () => {
    const { docId } = useParams<{ docId: string }>();
    const navigate = useNavigate();

    const [document, setDocument] = useState<Document | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [loadingDoc, setLoadingDoc] = useState(true);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const [isRecording, setIsRecording] = useState(false);

    const ttsService = getTTSService();

    useEffect(() => {
        if (docId) {
            loadDocument(docId);
        }
    }, [docId]);

    const loadDocument = async (id: string) => {
        try {
            const doc = await getDocument(id);
            setDocument(doc);
        } catch (error) {
            console.error('Failed to load document:', error);
            navigate('/documents');
        } finally {
            setLoadingDoc(false);
        }
    };

    const handleSend = useCallback(async (message: string) => {
        if (!docId) return;

        const userMessage: ChatMessage = {
            role: 'user',
            content: message,
            timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, userMessage]);
        setIsLoading(true);

        try {
            const response = await sendDocumentMessage(docId, {
                message,
                session_id: sessionId || undefined,
            });

            if (!sessionId) {
                setSessionId(response.session_id);
            }

            const assistantMessage: ChatMessage = {
                role: 'assistant',
                content: response.response,
                timestamp: new Date().toISOString(),
                sources: response.sources || undefined,
            };
            setMessages((prev) => [...prev, assistantMessage]);

            // Auto-play TTS for AI response
            if (response.response) {
                ttsService.speak(response.response, {
                    onStart: () => setIsSpeaking(true),
                    onEnd: () => setIsSpeaking(false)
                });
            }
        } catch (error) {
            console.error('Chat error:', error);
            const errorMessage: ChatMessage = {
                role: 'assistant',
                content: 'Sorry, I couldn\'t query this document. Please try again.',
                timestamp: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    }, [docId, sessionId, ttsService]);

    const handleVoiceTranscript = (transcript: string) => {
        setInputValue(transcript);
        setTimeout(() => handleSend(transcript), 500);
    };

    // Cleanup TTS on unmount
    useEffect(() => {
        return () => {
            ttsService.stop();
        };
    }, [ttsService]);

    if (loadingDoc) {
        return (
            <Container className="py-5 text-center">
                <Spinner animation="border" />
                <p className="mt-3">Loading document...</p>
            </Container>
        );
    }

    if (!document) {
        return (
            <Container className="py-5 text-center">
                <h4>Document not found</h4>
                <button className="btn btn-gradient mt-3" onClick={() => navigate('/documents')}>
                    Back to Documents
                </button>
            </Container>
        );
    }

    return (
        <Container className="py-4">
            <Row className="mb-4">
                <Col>
                    <button className="btn btn-glass mb-3" onClick={() => navigate('/documents')}>
                        ← Back to Documents
                    </button>
                    <h1 className="mb-1">{document.filename}</h1>
                    <div className="d-flex align-items-center gap-3">
                        <StatusBadge status={document.validation_status} />
                        {document.metadata?.vendor && (
                            <span className="text-secondary">🏢 {document.metadata.vendor}</span>
                        )}
                        {document.metadata?.total && (
                            <span className="text-secondary">
                                💰 {document.metadata.currency || '$'}{document.metadata.total.toFixed(2)}
                            </span>
                        )}
                    </div>
                </Col>
            </Row>

            <Row>
                <Col lg={8}>
                    <div className="chat-container" style={{ position: 'relative' }}>
                        <VoiceRecordingAnimation isRecording={isRecording} />
                        <VoiceAnimation isActive={isSpeaking} />
                        <ChatWindow
                            messages={messages}
                            isLoading={isLoading}
                            toolStatus={isLoading ? '🔎 Searching document...' : null}
                        />
                        <div className="d-flex gap-2">
                            <div className="flex-grow-1">
                                <ChatInput
                                    onSend={handleSend}
                                    disabled={isLoading}
                                    placeholder={`Ask a question about ${document.filename}...`}
                                    value={inputValue}
                                    onChange={setInputValue}
                                />
                            </div>
                            <VoiceButton
                                onTranscript={handleVoiceTranscript}
                                disabled={isLoading}
                                onRecordingChange={setIsRecording}
                            />
                        </div>
                    </div>
                </Col>

                <Col lg={4}>
                    <Card className="glass-card mb-4">
                        <Card.Body>
                            <h6 className="mb-3">📄 Document Info</h6>
                            <table className="table table-sm mb-0" style={{ background: 'transparent', color: 'white' }}>
                                <tbody>
                                    <tr>
                                        <td className="text-secondary" style={{ border: 'none', color: 'rgba(255,255,255,0.7)' }}>Type</td>
                                        <td style={{ border: 'none', color: 'white' }}>{document.file_type.toUpperCase()}</td>
                                    </tr>
                                    <tr>
                                        <td className="text-secondary" style={{ border: 'none', color: 'rgba(255,255,255,0.7)' }}>Uploaded</td>
                                        <td style={{ border: 'none', color: 'white' }}>{new Date(document.upload_timestamp).toLocaleString()}</td>
                                    </tr>
                                    {document.metadata?.invoice_number && (
                                        <tr>
                                            <td className="text-secondary" style={{ border: 'none', color: 'rgba(255,255,255,0.7)' }}>Invoice #</td>
                                            <td style={{ border: 'none', color: 'white' }}>{document.metadata.invoice_number}</td>
                                        </tr>
                                    )}
                                    {document.metadata?.date && (
                                        <tr>
                                            <td className="text-secondary" style={{ border: 'none', color: 'rgba(255,255,255,0.7)' }}>Date</td>
                                            <td style={{ border: 'none', color: 'white' }}>{new Date(document.metadata.date).toLocaleDateString()}</td>
                                        </tr>
                                    )}
                                    <tr>
                                        <td className="text-secondary" style={{ border: 'none', color: 'rgba(255,255,255,0.7)' }}>Content</td>
                                        <td style={{ border: 'none', color: 'white' }}>{document.raw_text_length || 0} chars</td>
                                    </tr>
                                </tbody>
                            </table>

                            {/* Show force-validate corrections if present */}
                            {document.forced_valid && document.admin_corrections && Object.keys(document.admin_corrections).length > 0 && (
                                <div className="mt-3 pt-3" style={{ borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                                    <h6 className="mb-2 text-warning">🔧 Admin Corrections</h6>
                                    <table className="table table-sm mb-0" style={{ background: 'transparent', color: 'white' }}>
                                        <tbody>
                                            {Object.entries(document.admin_corrections).map(([field, value]) => (
                                                <tr key={field}>
                                                    <td className="text-secondary" style={{ border: 'none', color: 'rgba(255,255,255,0.7)' }}>{field}</td>
                                                    <td style={{ border: 'none', color: 'white' }}>{String(value)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </Card.Body>
                    </Card>

                    <Card className="glass-card">
                        <Card.Body>
                            <h6 className="mb-3">💡 Try asking</h6>
                            <div className="d-grid gap-2">
                                <button
                                    className="btn btn-glass text-start btn-sm"
                                    onClick={() => handleSend('What is the total amount?')}
                                    disabled={isLoading}
                                >
                                    "What is the total amount?"
                                </button>
                                <button
                                    className="btn btn-glass text-start btn-sm"
                                    onClick={() => handleSend('Who is the vendor?')}
                                    disabled={isLoading}
                                >
                                    "Who is the vendor?"
                                </button>
                                <button
                                    className="btn btn-glass text-start btn-sm"
                                    onClick={() => handleSend('Is tax included?')}
                                    disabled={isLoading}
                                >
                                    "Is tax included?"
                                </button>
                                <button
                                    className="btn btn-glass text-start btn-sm"
                                    onClick={() => handleSend('Summarize this invoice')}
                                    disabled={isLoading}
                                >
                                    "Summarize this invoice"
                                </button>
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </Container>
    );
};

export default DocumentChat;
