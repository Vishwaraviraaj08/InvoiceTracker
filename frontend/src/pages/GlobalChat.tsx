// Global Chat Page

import { useState, useCallback, useEffect } from 'react';
import { Container, Row, Col, Card } from 'react-bootstrap';
import { ChatWindow, ChatInput } from '../components/Chat';
import { VoiceButton } from '../components/VoiceButton';
import { VoiceAnimation } from '../components/VoiceAnimation';
import { VoiceRecordingAnimation } from '../components/VoiceRecordingAnimation';
import { sendGlobalMessage } from '../services/api';
import { getTTSService } from '../utils/tts';
import type { ChatMessage } from '../types';

const GlobalChat = () => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [toolStatus, setToolStatus] = useState<string | null>(null);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const [isRecording, setIsRecording] = useState(false);

    const ttsService = getTTSService();

    const handleSend = useCallback(async (message: string) => {
        // Add user message
        const userMessage: ChatMessage = {
            role: 'user',
            content: message,
            timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, userMessage]);
        setIsLoading(true);
        setToolStatus('Processing...');

        try {
            const response = await sendGlobalMessage({
                message,
                session_id: sessionId || undefined,
            });

            // Update session ID
            if (!sessionId) {
                setSessionId(response.session_id);
            }

            // Update tool status while processing
            if (response.tool_used) {
                const toolLabels: Record<string, string> = {
                    validate_invoice: '🔍 Validating invoice...',
                    query_document: '📄 Querying document...',
                    list_invoices: '📋 Listing invoices...',
                    get_invoice_details: '📊 Getting details...',
                    general_chat: '💬 Generating response...',
                };
                setToolStatus(toolLabels[response.tool_used] || `Using: ${response.tool_used}`);
            }

            // Add assistant message
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

            // Handle clarification
            if (response.needs_clarification && response.clarification_question) {
                const clarificationMessage: ChatMessage = {
                    role: 'assistant',
                    content: response.clarification_question,
                    timestamp: new Date().toISOString(),
                };
                setMessages((prev) => [...prev, clarificationMessage]);
            }
        } catch (error) {
            console.error('Chat error:', error);
            const errorMessage: ChatMessage = {
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.',
                timestamp: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
            setToolStatus(null);
        }
    }, [sessionId, ttsService]);

    const handleVoiceTranscript = (transcript: string) => {
        setInputValue(transcript);
        // Auto-send after voice input
        setTimeout(() => handleSend(transcript), 500);
    };

    // Cleanup TTS on unmount
    useEffect(() => {
        return () => {
            ttsService.stop();
        };
    }, [ttsService]);

    return (
        <Container className="py-4">
            <Row className="mb-4">
                <Col>
                    <h1 className="mb-1">Global Chat</h1>
                    <p className="text-secondary">Ask anything about your invoices</p>
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
                            toolStatus={toolStatus}
                        />
                        <div className="d-flex gap-2">
                            <div className="flex-grow-1">
                                <ChatInput
                                    onSend={handleSend}
                                    disabled={isLoading}
                                    placeholder="Ask me to list invoices, validate a document, or answer questions..."
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
                            <h6 className="mb-3">💡 Example Questions</h6>
                            <div className="d-grid gap-2">
                                <button
                                    className="btn btn-glass text-start btn-sm"
                                    onClick={() => handleSend('List all my invoices')}
                                    disabled={isLoading}
                                >
                                    📋 List all my invoices
                                </button>
                                <button
                                    className="btn btn-glass text-start btn-sm"
                                    onClick={() => handleSend('Which invoices need validation?')}
                                    disabled={isLoading}
                                >
                                    ❓ Which invoices need validation?
                                </button>
                                <button
                                    className="btn btn-glass text-start btn-sm"
                                    onClick={() => handleSend('Export all invoices to Excel')}
                                    disabled={isLoading}
                                >
                                    📥 Export all invoices to Excel
                                </button>
                                <button
                                    className="btn btn-glass text-start btn-sm"
                                    onClick={() => handleSend('Help me understand invoice management')}
                                    disabled={isLoading}
                                >
                                    💡 Help me understand invoice management
                                </button>
                            </div>
                        </Card.Body>
                    </Card>

                    <Card className="glass-card">
                        <Card.Body>
                            <h6 className="mb-3">🤖 Capabilities</h6>
                            <ul className="text-secondary small ps-3 mb-0">
                                <li className="mb-1">List and search invoices</li>
                                <li className="mb-1">Validate invoice correctness</li>
                                <li className="mb-1">Get invoice details</li>
                                <li className="mb-1">Export to CSV/Excel</li>
                                <li className="mb-1">Answer general questions</li>
                                <li>Trigger document actions</li>
                            </ul>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </Container>
    );
};

export default GlobalChat;
