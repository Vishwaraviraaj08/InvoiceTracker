// Siri-like Voice Recording Animation

import './VoiceRecordingAnimation.css';

interface VoiceRecordingAnimationProps {
    isRecording: boolean;
}

export const VoiceRecordingAnimation = ({ isRecording }: VoiceRecordingAnimationProps) => {
    if (!isRecording) return null;

    return (
        <div className="voice-recording-overlay">
            <div className="voice-recording-container">
                <div className="siri-wave">
                    <div className="wave-bar bar-1"></div>
                    <div className="wave-bar bar-2"></div>
                    <div className="wave-bar bar-3"></div>
                    <div className="wave-bar bar-4"></div>
                    <div className="wave-bar bar-5"></div>
                    <div className="wave-bar bar-6"></div>
                    <div className="wave-bar bar-7"></div>
                    <div className="wave-bar bar-8"></div>
                    <div className="wave-bar bar-9"></div>
                </div>
                <p className="recording-text">Listening...</p>
                <p className="recording-hint">Speak now</p>
            </div>
        </div>
    );
};

export default VoiceRecordingAnimation;
