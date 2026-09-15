import type { SpeechToTextProvider, STTResult } from '../types';

// Web Speech API Types
interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: 'no-speech' | 'aborted' | 'audio-capture' | 'network' | 'not-allowed' | 'service-not-allowed' | 'bad-grammar' | 'language-not-supported';
  message: string;
}

interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => any) | null;
  onend: ((this: SpeechRecognition, ev: Event) => any) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

declare global {
  interface Window {
    SpeechRecognition: {
      prototype: SpeechRecognition;
      new (): SpeechRecognition;
    };
    webkitSpeechRecognition: {
      prototype: SpeechRecognition;
      new (): SpeechRecognition;
    };
  }
}

// ============================================================
// Speech-to-Text Service Abstraction
// ============================================================
// To add a new provider (e.g. Whisper):
// 1. Create a class implementing SpeechToTextProvider
// 2. Register it in SpeechToTextService
// ============================================================

type STTCallback = (result: STTResult) => void;
type ErrorCallback = (error: string) => void;
type StatusCallback = (status: 'listening' | 'stopped' | 'transcribing') => void;

// ---- Browser Web Speech API Provider ----

class BrowserSpeechProvider implements SpeechToTextProvider {
  private recognition: SpeechRecognition | null = null;
  private onResult: STTCallback | null = null;
  private onError: ErrorCallback | null = null;
  private onStatus: StatusCallback | null = null;

  isAvailable(): boolean {
    return !!(
      'SpeechRecognition' in window ||
      'webkitSpeechRecognition' in window
    );
  }

  configure(
    onResult: STTCallback,
    onError: ErrorCallback,
    onStatus: StatusCallback,
  ) {
    this.onResult = onResult;
    this.onError = onError;
    this.onStatus = onStatus;
  }

  start(language = 'en-US'): void {
    if (!this.isAvailable()) {
      this.onError?.('Speech recognition is not supported in this browser.');
      return;
    }

    const SpeechRecognition =
      window.SpeechRecognition || (window as any).webkitSpeechRecognition;

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = true;
    this.recognition.lang = language;
    this.recognition.maxAlternatives = 1;

    this.recognition.onstart = () => {
      this.onStatus?.('listening');
    };

    this.recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }

      if (finalTranscript) {
        this.onResult?.({
          transcript: finalTranscript.trim(),
          confidence: event.results[event.results.length - 1][0].confidence,
          isFinal: true,
        });
      } else if (interimTranscript) {
        this.onResult?.({
          transcript: interimTranscript.trim(),
          confidence: 0,
          isFinal: false,
        });
      }
    };

    this.recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const messages: Record<string, string> = {
        'not-allowed': 'Microphone access was denied. Please allow microphone access in your browser settings.',
        'no-speech': 'No speech was detected. Please try again.',
        'network': 'A network error occurred during speech recognition.',
        'audio-capture': 'No microphone was found. Please connect a microphone.',
        'aborted': '',
      };
      const msg = messages[event.error] ?? `Speech recognition error: ${event.error}`;
      if (msg) this.onError?.(msg);
    };

    this.recognition.onend = () => {
      this.onStatus?.('stopped');
    };

    try {
      this.recognition.start();
    } catch (e) {
      this.onError?.('Failed to start speech recognition. Please try again.');
    }
  }

  stop(): void {
    if (this.recognition) {
      this.recognition.stop();
      this.recognition = null;
    }
  }
}

// ---- Future: Whisper Provider Placeholder ----
// class WhisperProvider implements SpeechToTextProvider {
//   isAvailable(): boolean { return true; }
//   start(language?: string): void { /* POST audio to /api/stt/whisper */ }
//   stop(): void { /* stop recording */ }
// }

// ---- Public Service ----

export class SpeechToTextService {
  private provider: BrowserSpeechProvider;

  constructor() {
    this.provider = new BrowserSpeechProvider();
  }

  isAvailable(): boolean {
    return this.provider.isAvailable();
  }

  configure(
    onResult: STTCallback,
    onError: ErrorCallback,
    onStatus: StatusCallback,
  ) {
    this.provider.configure(onResult, onError, onStatus);
  }

  start(language = 'en-US'): void {
    this.provider.start(language);
  }

  stop(): void {
    this.provider.stop();
  }
}

// Singleton
export const sttService = new SpeechToTextService();

// Map language codes to BCP-47 locale codes for the Web Speech API
export const languageToLocale: Record<string, string> = {
  en: 'en-US',
  ta: 'ta-IN',
  hi: 'hi-IN',
  te: 'te-IN',
  ml: 'ml-IN',
  kn: 'kn-IN',
  bn: 'bn-IN',
  mr: 'mr-IN',
  es: 'es-ES',
  fr: 'fr-FR',
  de: 'de-DE',
  ja: 'ja-JP',
  zh: 'zh-CN',
  ar: 'ar-SA',
  pt: 'pt-BR',
  ru: 'ru-RU',
  ko: 'ko-KR',
  it: 'it-IT',
};
