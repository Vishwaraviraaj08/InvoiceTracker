// Voice Button Component with recording functionality

import { useState, useRef } from 'react';
import { Button } from 'react-bootstrap';

interface VoiceButtonProps {
    onTranscript: (text: string) => void;
    disabled?: boolean;
    onRecordingChange?: (isRecording: boolean) => void;
}

export const VoiceButton = ({ onTranscript, disabled, onRecordingChange }: VoiceButtonProps) => {
    const [isRecording, setIsRecording] = useState(false);
    const recognitionRef = useRef<any>(null);

    const updateRecordingState = (recording: boolean) => {
        setIsRecording(recording);
        if (onRecordingChange) {
            onRecordingChange(recording);
        }
    };

    const startRecording = () => {
        // Check browser support
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

        if (!SpeechRecognition) {
            alert('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            updateRecordingState(true);
        };

        recognition.onresult = (event: any) => {
            const transcript = event.results[0][0].transcript;
            onTranscript(transcript);
            updateRecordingState(false);
        };

        recognition.onerror = (event: any) => {
            console.error('Speech recognition error:', event.error);
            updateRecordingState(false);
            if (event.error === 'no-speech') {
                alert('No speech detected. Please try again.');
            } else {
                alert(`Error: ${event.error}`);
            }
        };

        recognition.onend = () => {
            updateRecordingState(false);
        };

        recognitionRef.current = recognition;
        recognition.start();
    };

    const stopRecording = () => {
        if (recognitionRef.current) {
            recognitionRef.current.stop();
        }
        updateRecordingState(false);
    };

    return (
        <Button
            variant={isRecording ? 'danger' : 'outline-primary'}
            size="sm"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={disabled}
            className={`voice-button ${isRecording ? 'recording' : ''}`}
            title={isRecording ? 'Stop recording' : 'Start voice input'}
        >
            {isRecording ? (
                <>
                    <span className="recording-pulse"></span>
                    🎙️ Stop
                </>
            ) : (
                '🎤 Voice'
            )}
            <style>{`
                .voice-button {
                    position: relative;
                    transition: all 0.3s ease;
                }
                .voice-button.recording {
                    animation: pulse-button 1.5s ease-in-out infinite;
                }
                .recording-pulse {
                    position: absolute;
                    top: -4px;
                    right: -4px;
                    width: 10px;
                    height: 10px;
                    background: #ef4444;
                    border-radius: 50%;
                    animation: pulse-dot 1s ease-in-out infinite;
                }
                @keyframes pulse-button {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                }
                @keyframes pulse-dot {
                    0%, 100% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.5; transform: scale(1.2); }
                }
            `}</style>
        </Button>
    );
};

export default VoiceButton;
