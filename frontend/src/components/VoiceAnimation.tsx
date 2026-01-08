// Voice Animation Component - Beautiful pulsing orb while AI speaks

import './VoiceAnimation.css';

interface VoiceAnimationProps {
    isActive: boolean;
}

export const VoiceAnimation = ({ isActive }: VoiceAnimationProps) => {
    if (!isActive) return null;

    return (
        <div className="voice-animation-container">
            <div className="voice-orb">
                <div className="orb-core"></div>
                <div className="orb-ring ring-1"></div>
                <div className="orb-ring ring-2"></div>
                <div className="orb-ring ring-3"></div>
            </div>
            <p className="voice-status">AI is speaking...</p>
        </div>
    );
};

export default VoiceAnimation;
