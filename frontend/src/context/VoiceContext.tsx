// Voice Context for global Voice Answer Mode state

import { createContext, useContext, useState, type ReactNode } from 'react';

interface VoiceContextType {
    voiceEnabled: boolean;
    setVoiceEnabled: (enabled: boolean) => void;
    toggleVoice: () => void;
}

const VoiceContext = createContext<VoiceContextType | null>(null);

export const VoiceProvider = ({ children }: { children: ReactNode }) => {
    const [voiceEnabled, setVoiceEnabled] = useState(true);

    const toggleVoice = () => setVoiceEnabled(prev => !prev);

    return (
        <VoiceContext.Provider value={{ voiceEnabled, setVoiceEnabled, toggleVoice }}>
            {children}
        </VoiceContext.Provider>
    );
};

export const useVoiceMode = () => {
    const context = useContext(VoiceContext);
    if (!context) {
        throw new Error('useVoiceMode must be used within a VoiceProvider');
    }
    return context;
};
