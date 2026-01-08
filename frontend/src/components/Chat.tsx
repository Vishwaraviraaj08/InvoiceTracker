// Chat Components

import { useState, useRef, useEffect } from 'react';
import { Spinner } from 'react-bootstrap';
import ReactMarkdown from 'react-markdown';
import type { ChatMessage } from '../types';

interface ChatWindowProps {
    messages: ChatMessage[];
    isLoading: boolean;
    toolStatus?: string | null;
}

export const ChatWindow = ({ messages, isLoading, toolStatus }: ChatWindowProps) => {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    return (
        <div className="chat-messages">
            {messages.length === 0 && (
                <div className="text-center text-secondary py-5">
                    <h5>👋 Start a conversation</h5>
                    <p>Ask me anything about your invoices!</p>
                </div>
            )}

            {messages.map((msg, index) => (
                <MessageBubble key={msg.id || index} message={msg} />
            ))}

            {isLoading && (
                <div className="message-bubble message-assistant">
                    <div className="d-flex align-items-center gap-2">
                        <Spinner animation="border" size="sm" />
                        {toolStatus && <span className="tool-status">{toolStatus}</span>}
                        {!toolStatus && <span>Thinking...</span>}
                    </div>
                </div>
            )}

            <div ref={messagesEndRef} />
        </div>
    );
};

interface MessageBubbleProps {
    message: ChatMessage;
}

export const MessageBubble = ({ message }: MessageBubbleProps) => {
    const isUser = message.role === 'user';

    return (
        <div className={`message-bubble ${isUser ? 'message-user' : 'message-assistant'}`}>
            <div className="message-content markdown-content">
                {isUser ? (
                    // User messages: plain text
                    <p className="mb-0">{message.content}</p>
                ) : (
                    // Assistant messages: render as markdown
                    <ReactMarkdown
                        components={{
                            // Custom rendering for various elements
                            h1: ({ children }) => <h4 className="mb-2 mt-3">{children}</h4>,
                            h2: ({ children }) => <h5 className="mb-2 mt-3">{children}</h5>,
                            h3: ({ children }) => <h6 className="mb-2 mt-2">{children}</h6>,
                            p: ({ children }) => <p className="mb-2">{children}</p>,
                            ul: ({ children }) => <ul className="mb-2 ps-3">{children}</ul>,
                            ol: ({ children }) => <ol className="mb-2 ps-3">{children}</ol>,
                            li: ({ children }) => <li className="mb-1">{children}</li>,
                            strong: ({ children }) => <strong className="fw-bold">{children}</strong>,
                            a: ({ href, children }) => (
                                <a href={href} target="_blank" rel="noopener noreferrer" className="text-info">
                                    {children}
                                </a>
                            ),
                            code: ({ children, className }) => {
                                const isInline = !className;
                                return isInline ? (
                                    <code className="bg-dark px-1 rounded">{children}</code>
                                ) : (
                                    <pre className="bg-dark p-2 rounded overflow-auto">
                                        <code>{children}</code>
                                    </pre>
                                );
                            },
                            blockquote: ({ children }) => (
                                <blockquote className="border-start border-3 border-info ps-3 my-2 text-secondary">
                                    {children}
                                </blockquote>
                            ),
                            hr: () => <hr className="my-3 border-secondary" />,
                            table: ({ children }) => (
                                <div className="table-responsive">
                                    <table className="table table-sm table-dark">{children}</table>
                                </div>
                            ),
                        }}
                    >
                        {message.content}
                    </ReactMarkdown>
                )}
            </div>

            {message.sources && message.sources.length > 0 && (
                <div className="mt-2 pt-2 border-top border-secondary">
                    <small className="text-secondary">Sources:</small>
                    <ul className="list-unstyled mb-0 mt-1">
                        {message.sources.slice(0, 2).map((source, i) => (
                            <li key={i}>
                                <small className="text-secondary">• {source}</small>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

interface ChatInputProps {
    onSend: (message: string) => void;
    disabled: boolean;
    placeholder?: string;
    value?: string;
    onChange?: (value: string) => void;
}

export const ChatInput = ({ onSend, disabled, placeholder, value: controlledValue, onChange }: ChatInputProps) => {
    const [internalValue, setInternalValue] = useState('');

    // Use controlled value if provided, otherwise use internal state
    const inputValue = controlledValue !== undefined ? controlledValue : internalValue;
    const setInputValue = onChange || setInternalValue;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (inputValue.trim() && !disabled) {
            onSend(inputValue.trim());
            setInputValue('');
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="chat-input-form">
            <div className="input-group">
                <input
                    type="text"
                    className="form-control chat-input"
                    placeholder={placeholder || "Type your message..."}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyPress={handleKeyPress}
                    disabled={disabled}
                />
                <button
                    type="submit"
                    className="btn btn-gradient"
                    disabled={disabled || !inputValue.trim()}
                >
                    Send
                </button>
            </div>
        </form>
    );
};
