// ============================================================
// Shared TypeScript types for the Multilingual AI Assistant
// ============================================================

export type MessageRole = 'user' | 'assistant';

export type AppStatus =
  | 'idle'
  | 'listening'
  | 'transcribing'
  | 'thinking'
  | 'speaking'
  | 'error';

export interface SourceDocument {
  id: string;
  title: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  language: string;
  timestamp: Date;
  sources?: SourceDocument[];
  isLoading?: boolean;
}

export interface Language {
  code: string;
  name: string;
}

// ---------------- API Types ----------------

export interface ConversationTurn {
  role: MessageRole;
  content: string;
}

export interface ChatRequest {
  message: string;
  language?: string | null; // null = auto-detect
  conversation: ConversationTurn[];
}

export interface ChatResponse {
  answer: string;
  language: string;
  detected_language?: string;
  sources: SourceDocument[];
}

export interface HealthResponse {
  status: string;
  llm_provider: string;
  llm_available: boolean;
  model?: string;
}

export interface DetectLanguageResponse {
  language: string;
  language_name: string;
  confidence: string;
}

export interface STTResponse {
  transcript: string;
  detected_language: string;
  confidence: number;
}

// ---------------- STT Types ----------------

export type STTStatus = 'idle' | 'listening' | 'transcribing' | 'error';

export interface STTResult {
  transcript: string;
  confidence: number;
  isFinal: boolean;
}

export interface SpeechToTextProvider {
  start(language?: string): void;
  stop(): void;
  isAvailable(): boolean;
}

// ---------------- TTS Types ----------------

export type TTSStatus = 'idle' | 'playing' | 'paused' | 'stopped' | 'unavailable';

export interface TextToSpeechProvider {
  speak(text: string, language?: string): void;
  pause(): void;
  resume(): void;
  stop(): void;
  isAvailable(): boolean;
}
