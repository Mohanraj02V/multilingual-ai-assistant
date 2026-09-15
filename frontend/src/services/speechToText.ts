import type { SpeechToTextProvider, STTResult } from '../types';
import { transcribeAudio } from './api';

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
type DetectedLanguageCallback = (lang: string) => void;
type VolumeCallback = (volume: number) => void;

interface SpeechToTextProvider {
  isAvailable(): boolean;
  configure(
    onResult: STTCallback,
    onError: ErrorCallback,
    onStatus: StatusCallback,
    onDetectedLanguage?: DetectedLanguageCallback,
    onVolumeChange?: VolumeCallback
  ): void;
  start(language?: string): void;
  stop(): void;
}

// ---- Browser Web Speech API Provider ----

class BrowserSpeechProvider implements SpeechToTextProvider {
  private recognition: SpeechRecognition | null = null;
  private onResult: STTCallback | null = null;
  private onError: ErrorCallback | null = null;
  private onStatus: StatusCallback | null = null;
  private onStatus: StatusCallback | null = null;
  private onDetectedLanguage: DetectedLanguageCallback | null = null;
  private onVolumeChange: VolumeCallback | null = null;

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
    onDetectedLanguage?: DetectedLanguageCallback,
    onVolumeChange?: VolumeCallback
  ) {
    this.onResult = onResult;
    this.onError = onError;
    this.onStatus = onStatus;
    if (onDetectedLanguage) this.onDetectedLanguage = onDetectedLanguage;
    if (onVolumeChange) this.onVolumeChange = onVolumeChange;
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

// ---- Whisper API Provider ----
class WhisperSpeechProvider implements SpeechToTextProvider {
  private mediaRecorder: MediaRecorder | null = null;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private animationFrameId: number | null = null;
  private chunks: Blob[] = [];
  private onResult: STTCallback | null = null;
  private onError: ErrorCallback | null = null;
  private onStatus: StatusCallback | null = null;
  private onDetectedLanguage: DetectedLanguageCallback | null = null;
  private onVolumeChange: VolumeCallback | null = null;
  private maxDurationTimeout: number | null = null;
  private languageHint: string | undefined;

  isAvailable(): boolean {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  }

  configure(
    onResult: STTCallback,
    onError: ErrorCallback,
    onStatus: StatusCallback,
    onDetectedLanguage?: DetectedLanguageCallback,
    onVolumeChange?: VolumeCallback
  ) {
    this.onResult = onResult;
    this.onError = onError;
    this.onStatus = onStatus;
    if (onDetectedLanguage) this.onDetectedLanguage = onDetectedLanguage;
    if (onVolumeChange) this.onVolumeChange = onVolumeChange;
  }

  async start(languageHint?: string): Promise<void> {
    if (!this.isAvailable()) {
      this.onError?.('Microphone access is not supported in this browser.');
      return;
    }
    
    this.languageHint = languageHint;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.chunks = [];
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : ''
      });

      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.chunks.push(e.data);
      };

      // Set up Audio Analyser for volume visualization
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const source = this.audioContext.createMediaStreamSource(stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      source.connect(this.analyser);
      
      const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      const updateVolume = () => {
        if (!this.analyser || this.mediaRecorder?.state !== 'recording') return;
        this.analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const average = sum / dataArray.length;
        const normalized = Math.min(1, average / 128); // scale 0 to 1
        this.onVolumeChange?.(normalized);
        this.animationFrameId = requestAnimationFrame(updateVolume);
      };

      this.mediaRecorder.onstop = async () => {
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
        
        if (this.maxDurationTimeout) {
          window.clearTimeout(this.maxDurationTimeout);
          this.maxDurationTimeout = null;
        }

        const blob = new Blob(this.chunks, { type: this.mediaRecorder?.mimeType || 'audio/webm' });
        if (blob.size === 0) {
          this.onStatus?.('stopped');
          return;
        }

        this.onStatus?.('transcribing');

        try {
          const res = await transcribeAudio(blob, this.languageHint);
          this.onStatus?.('stopped');
          
          if (res.detected_language) {
            this.onDetectedLanguage?.(res.detected_language);
          }
          
          this.onResult?.({
            transcript: res.transcript,
            confidence: res.confidence,
            isFinal: true,
          });
        } catch (e: any) {
          this.onStatus?.('stopped');
          const msg = e.message === 'no-speech' 
            ? 'No speech was detected. Please try again.' 
            : `Transcription failed: ${e.message}`;
          this.onError?.(msg);
        }
      };

      this.mediaRecorder.start();
      this.onStatus?.('listening');
      updateVolume(); // Start the visualizer loop
      
      // Max recording duration: 30 seconds
      this.maxDurationTimeout = window.setTimeout(() => {
        if (this.mediaRecorder?.state === 'recording') {
          this.stop();
        }
      }, 30000);

    } catch (e: any) {
      if (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError') {
        this.onError?.('Microphone access was denied. Please allow microphone access in your browser settings.');
      } else {
        this.onError?.('Failed to start microphone.');
      }
    }
  }

  stop(): void {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    } else {
      // If we stop before anything started, ensure we reset status
      this.onStatus?.('stopped');
    }
    
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.onVolumeChange?.(0);
  }
}

// ---- Public Service ----

export class SpeechToTextService {
  private browserProvider: BrowserSpeechProvider;
  private whisperProvider: WhisperSpeechProvider;
  private activeProvider: SpeechToTextProvider | null = null;
  private configuredOnError: ErrorCallback | null = null;
  private configuredLanguage: string | undefined;

  constructor() {
    this.browserProvider = new BrowserSpeechProvider();
    this.whisperProvider = new WhisperSpeechProvider();
  }

  isAvailable(): boolean {
    return this.browserProvider.isAvailable() || this.whisperProvider.isAvailable();
  }

  configure(
    onResult: STTCallback,
    onError: ErrorCallback,
    onStatus: StatusCallback,
    onDetectedLanguage?: DetectedLanguageCallback,
    onVolumeChange?: VolumeCallback
  ) {
    this.configuredOnError = onError;
    // We configure both, but they will only fire when they are the active provider calling the callback
    this.browserProvider.configure(onResult, (err) => {
      // If browser STT fails with unsupported language and it wasn't auto, fallback to Whisper
      if (err.includes('language-not-supported') || err.includes('not supported in this browser')) {
        console.warn('Browser STT failed, falling back to Whisper...', err);
        this.activeProvider = this.whisperProvider;
        this.whisperProvider.start(this.configuredLanguage);
      } else {
        onError(err);
      }
    }, onStatus, onDetectedLanguage, onVolumeChange);
    
    this.whisperProvider.configure(onResult, onError, onStatus, onDetectedLanguage, onVolumeChange);
  }

  start(language = 'auto'): void {
    this.configuredLanguage = language;
    if (language === 'auto') {
      this.activeProvider = this.whisperProvider;
      this.whisperProvider.start('auto');
    } else {
      // Check if code maps to a locale
      const locale = languageToLocale[language];
      if (!locale) {
        // Unknown language code, use Whisper
        this.activeProvider = this.whisperProvider;
        this.whisperProvider.start(language);
        return;
      }
      this.activeProvider = this.browserProvider;
      this.browserProvider.start(locale);
    }
  }

  stop(): void {
    if (this.activeProvider) {
      this.activeProvider.stop();
    }
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
