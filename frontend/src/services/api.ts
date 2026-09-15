/// <reference types="vite/client" />
import type {
  ChatRequest,
  HealthResponse,
  DetectLanguageResponse,
  STTResponse,
  Language,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

async function fetchJSON<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // ignore parse errors
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

// ---- Public API functions ----

// Indic script ranges — used for grapheme-safe buffering
const INDIC_SCRIPT_RANGES = /[\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0A80-\u0AFF\u0B00-\u0B7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F]/;

function containsIndicScript(text: string): boolean {
  return INDIC_SCRIPT_RANGES.test(text);
}

/**
 * Split text into safe grapheme clusters for rendering.
 * Uses Intl.Segmenter when available (all modern browsers).
 * Falls back to Array.from() which handles Unicode codepoints but not combining marks.
 */
function safeGraphemeSplit(text: string): string[] {
  if (typeof Intl !== 'undefined' && 'Segmenter' in Intl) {
    const segmenter = new (Intl as any).Segmenter(undefined, { granularity: 'grapheme' });
    return Array.from(segmenter.segment(text), (s: any) => s.segment);
  }
  return Array.from(text);
}

export interface StreamChatCallbacks {
  onMeta: (meta: { detected_language: string; language: string; sources: Array<{ id: string; title: string }> }) => void;
  onToken: (token: string) => void;
  onThinking: () => void;
  onTranslating: () => void;
  onDone: () => void;
  onError: (detail: string) => void;
}

/**
 * Send a chat message and stream the response via SSE.
 *
 * Grapheme-safe rendering:
 * - For Indic scripts, tokens are buffered until a complete grapheme cluster boundary
 *   is reached before calling onToken. This prevents flashing of broken half-characters
 *   (combining vowel signs, etc.) for Tamil, Hindi, Telugu, Malayalam, etc.
 * - For Latin/high-resource scripts, tokens are passed through immediately.
 */
export async function streamChatMessage(
  request: ChatRequest,
  callbacks: StreamChatCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch { /* ignore */ }
    throw new Error(message);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let graphemeBuffer = '';
  let useIndicSafe = false;

  const flushGraphemeBuffer = () => {
    if (graphemeBuffer) {
      callbacks.onToken(graphemeBuffer);
      graphemeBuffer = '';
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';  // keep incomplete line in buffer

      let currentEventType = 'message';
      for (const line of lines) {
        if (line.startsWith('event:')) {
          currentEventType = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          const rawData = line.slice(5).trim();

          if (rawData === '[DONE]') {
            flushGraphemeBuffer();
            callbacks.onDone();
            return;
          }

          if (currentEventType === 'meta') {
            try {
              const meta = JSON.parse(rawData);
              useIndicSafe = containsIndicScript('test') || ['ta', 'hi', 'te', 'ml', 'kn', 'bn', 'mr'].includes(meta.language);
              callbacks.onMeta(meta);
            } catch { /* ignore */ }
          } else if (currentEventType === 'thinking') {
            callbacks.onThinking();
          } else if (currentEventType === 'translating') {
            useIndicSafe = true; // Indic translation about to start
            callbacks.onTranslating();
          } else if (currentEventType === 'error') {
            try {
              const err = JSON.parse(rawData);
              callbacks.onError(err.detail || 'Unknown error');
            } catch {
              callbacks.onError(rawData);
            }
            return;
          } else {
            // Content token
            try {
              const token = JSON.parse(rawData);
              if (useIndicSafe) {
                // Buffer tokens until we have complete grapheme clusters
                graphemeBuffer += token;
                const graphemes = safeGraphemeSplit(graphemeBuffer);
                // Keep the last grapheme buffered in case it's a combining character
                // that hasn't been completed yet by the next token
                if (graphemes.length > 1) {
                  const safeToRender = graphemes.slice(0, -1).join('');
                  const possiblyIncomplete = graphemes[graphemes.length - 1];
                  callbacks.onToken(safeToRender);
                  graphemeBuffer = possiblyIncomplete;
                }
              } else {
                callbacks.onToken(token);
              }
            } catch { /* ignore */ }
          }
          // Reset event type after data line
          currentEventType = 'message';
        } else if (line === '') {
          // End of SSE event block — reset type
          currentEventType = 'message';
        }
      }
    }
    // Flush any remaining grapheme buffer
    flushGraphemeBuffer();
    callbacks.onDone();
  } finally {
    reader.releaseLock();
  }
}

/**
 * Check backend and LLM health.
 */
export async function checkHealth(): Promise<HealthResponse> {
  return fetchJSON<HealthResponse>('/health');
}

/**
 * Detect the language of a piece of text.
 */
export async function detectLanguage(text: string): Promise<DetectLanguageResponse> {
  return fetchJSON<DetectLanguageResponse>('/language/detect', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

/**
 * Get all supported languages.
 */
export async function getSupportedLanguages(): Promise<{ languages: Language[] }> {
  return fetchJSON<{ languages: Language[] }>('/languages');
}

/**
 * Transcribe audio using backend Whisper API.
 */
export async function transcribeAudio(blob: Blob, languageHint?: string): Promise<STTResponse> {
  const formData = new FormData();
  formData.append('audio', blob, 'audio.webm');
  if (languageHint && languageHint !== 'auto') {
    formData.append('language', languageHint);
  }

  const response = await fetch(`${BASE_URL}/stt/transcribe`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // ignore parse errors
    }
    throw new Error(message);
  }

  return response.json() as Promise<STTResponse>;
}
