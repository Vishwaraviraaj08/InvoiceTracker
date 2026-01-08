// Text-to-Speech Utility using Web Speech Synthesis API

export class TextToSpeechService {
    private synthesis: SpeechSynthesis;
    private currentUtterance: SpeechSynthesisUtterance | null = null;
    private onStartCallback: (() => void) | null = null;
    private onEndCallback: (() => void) | null = null;

    constructor() {
        this.synthesis = window.speechSynthesis;
    }

    speak(text: string, options?: {
        rate?: number;
        pitch?: number;
        volume?: number;
        voice?: SpeechSynthesisVoice;
        onStart?: () => void;
        onEnd?: () => void;
    }) {
        // Cancel any ongoing speech
        this.stop();

        const utterance = new SpeechSynthesisUtterance(text);

        // Set options
        utterance.rate = options?.rate || 1.0;
        utterance.pitch = options?.pitch || 1.0;
        utterance.volume = options?.volume || 1.0;

        if (options?.voice) {
            utterance.voice = options.voice;
        }

        // Set callbacks
        this.onStartCallback = options?.onStart || null;
        this.onEndCallback = options?.onEnd || null;

        utterance.onstart = () => {
            if (this.onStartCallback) {
                this.onStartCallback();
            }
        };

        utterance.onend = () => {
            if (this.onEndCallback) {
                this.onEndCallback();
            }
            this.currentUtterance = null;
        };

        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event);
            if (this.onEndCallback) {
                this.onEndCallback();
            }
            this.currentUtterance = null;
        };

        this.currentUtterance = utterance;
        this.synthesis.speak(utterance);
    }

    stop() {
        if (this.synthesis.speaking) {
            this.synthesis.cancel();
        }
        this.currentUtterance = null;
    }

    pause() {
        if (this.synthesis.speaking) {
            this.synthesis.pause();
        }
    }

    resume() {
        if (this.synthesis.paused) {
            this.synthesis.resume();
        }
    }

    isSpeaking(): boolean {
        return this.synthesis.speaking;
    }

    getVoices(): SpeechSynthesisVoice[] {
        return this.synthesis.getVoices();
    }

    // Get a good default English voice
    getDefaultVoice(): SpeechSynthesisVoice | null {
        const voices = this.getVoices();

        // Try to find a good English voice
        const preferredVoices = [
            voices.find(v => v.name.includes('Google US English')),
            voices.find(v => v.name.includes('Microsoft Zira')),
            voices.find(v => v.lang === 'en-US'),
            voices.find(v => v.lang.startsWith('en'))
        ];

        return preferredVoices.find(v => v !== undefined) || voices[0] || null;
    }
}

// Global instance
let ttsService: TextToSpeechService | null = null;

export const getTTSService = (): TextToSpeechService => {
    if (!ttsService) {
        ttsService = new TextToSpeechService();
    }
    return ttsService;
};

export default getTTSService;
