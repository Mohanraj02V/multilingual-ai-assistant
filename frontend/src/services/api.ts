/// <reference types="vite/client" />
import type {
  ChatRequest,
  ChatResponse,
  HealthResponse,
  DetectLanguageResponse,
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

/**
 * Send a chat message and receive an AI response.
 */
export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  return fetchJSON<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify(request),
  });
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
