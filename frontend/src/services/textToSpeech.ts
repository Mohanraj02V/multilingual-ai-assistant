import type { TTSStatus } from '../types';

// ============================================================
// Text-to-Speech Service Abstraction
// ============================================================
// To add a new provider (e.g. ElevenLabs, Google TTS):
// 1. Create a class below
// 2. Register it in TextToSpeechService
// ============================================================

type TTSStatusCallback = (status: TTSStatus) => void;

// ---- Browser SpeechSynthesis Provider ----

class BrowserTTSProvider {
  private utterance: SpeechSynthesisUtterance | null = null;
  private onStatus: TTSStatusCallback | null = null;

  isAvailable(): boolean {
    return 'speechSynthesis' in window;
  }

  configure(onStatus: TTSStatusCallback) {
    this.onStatus = onStatus;
  }

  speak(text: string, language = 'en'): void {
    if (!this.isAvailable()) {
      this.onStatus?.('unavailable');
      return;
    }

    // Stop any ongoing speech
    this.stop();

    this.utterance = new SpeechSynthesisUtterance(text);

    // Select the best matching voice
    const voice = this._selectVoice(language);
    if (voice) {
      this.utterance.voice = voice;
    }

    this.utterance.lang = this._getLocale(language);
    this.utterance.rate = 0.95;
    this.utterance.pitch = 1.0;
    this.utterance.volume = 1.0;

    this.utterance.onstart = () => this.onStatus?.('playing');
    this.utterance.onend = () => this.onStatus?.('stopped');
    this.utterance.onerror = (e) => {
      if (e.error !== 'interrupted') {
        console.warn('TTS error:', e.error);
      }
      this.onStatus?.('stopped');
    };

    window.speechSynthesis.speak(this.utterance);
  }

  pause(): void {
    if (this.isAvailable() && window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
      this.onStatus?.('paused');
    }
  }

  resume(): void {
    if (this.isAvailable() && window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      this.onStatus?.('playing');
    }
  }

  stop(): void {
    if (this.isAvailable()) {
      window.speechSynthesis.cancel();
      this.utterance = null;
      this.onStatus?.('stopped');
    }
  }

  private _getLocale(langCode: string): string {
    const localeMap: Record<string, string> = {
      en: 'en-US', ta: 'ta-IN', hi: 'hi-IN', te: 'te-IN',
      ml: 'ml-IN', kn: 'kn-IN', bn: 'bn-IN', mr: 'mr-IN',
      es: 'es-ES', fr: 'fr-FR', de: 'de-DE', ja: 'ja-JP',
      zh: 'zh-CN', ar: 'ar-SA', pt: 'pt-BR', ru: 'ru-RU',
      ko: 'ko-KR', it: 'it-IT',
    };
    return localeMap[langCode] ?? 'en-US';
  }

  private _selectVoice(langCode: string): SpeechSynthesisVoice | null {
    const voices = window.speechSynthesis.getVoices();
    const locale = this._getLocale(langCode);
    const langPrefix = locale.split('-')[0];

    // Try exact locale match first
    let voice = voices.find((v) => v.lang === locale);
    if (voice) return voice;

    // Try language prefix match
    voice = voices.find((v) => v.lang.startsWith(langPrefix));
    if (voice) return voice;

    // Fall back to any English voice
    return voices.find((v) => v.lang.startsWith('en')) ?? null;
  }
}

// ---- Future: External TTS Provider Placeholder ----
// class ExternalTTSProvider {
//   speak(text: string, language?: string): void { /* call cloud API */ }
//   ...
// }

// ---- Public Service ----

export class TextToSpeechService {
  private provider: BrowserTTSProvider;

  constructor() {
    this.provider = new BrowserTTSProvider();
  }

  isAvailable(): boolean {
    return this.provider.isAvailable();
  }

  configure(onStatus: TTSStatusCallback) {
    this.provider.configure(onStatus);
  }

  speak(text: string, language = 'en'): void {
    this.provider.speak(text, language);
  }

  pause(): void {
    this.provider.pause();
  }

  resume(): void {
    this.provider.resume();
  }

  stop(): void {
    this.provider.stop();
  }
}

// Singleton
export const ttsService = new TextToSpeechService();
