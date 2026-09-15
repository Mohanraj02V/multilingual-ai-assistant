import { useState, useCallback, useRef, useEffect } from 'react';
import { streamChatMessage, checkHealth } from '../services/api';
import type {
  Message,
  AppStatus,
  ConversationTurn,
} from '../types';

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

interface UseChatReturn {
  messages: Message[];
  status: AppStatus;
  selectedLanguage: string;
  setSelectedLanguage: (lang: string) => void;
  sendMessage: (content: string, detectedLanguage?: string) => Promise<void>;
  isLLMAvailable: boolean | null;
  clearConversation: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<AppStatus>('idle');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('auto');
  const [isLLMAvailable, setIsLLMAvailable] = useState<boolean | null>(null);
  const isProcessing = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Check LLM health on first send (lazy) or on mount
  const ensureHealthChecked = useCallback(async () => {
    if (isLLMAvailable !== null) return;
    try {
      const health = await checkHealth();
      setIsLLMAvailable(health.llm_available);
    } catch {
      setIsLLMAvailable(false);
    }
  }, [isLLMAvailable]);

  // Check health on mount
  useEffect(() => {
    ensureHealthChecked();
  }, [ensureHealthChecked]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const sendMessage = useCallback(
    async (content: string, detectedLanguage?: string) => {
      const trimmed = content.trim();
      if (!trimmed || isProcessing.current) return;

      isProcessing.current = true;
      await ensureHealthChecked();

      // Add user message
      const userMessage: Message = {
        id: generateId(),
        role: 'user',
        content: trimmed,
        language: selectedLanguage === 'auto' ? (detectedLanguage || 'en') : selectedLanguage,
        timestamp: new Date(),
      };

      // Add streaming placeholder for assistant
      const loadingId = generateId();
      const loadingMessage: Message = {
        id: loadingId,
        role: 'assistant',
        content: '',
        language: 'en',
        timestamp: new Date(),
        isLoading: true,
      };

      setMessages((prev) => [...prev, userMessage, loadingMessage]);
      setStatus('thinking');

      // Build conversation history (exclude loading messages)
      const historyMessages = messages.filter((m) => !m.isLoading);
      const conversation: ConversationTurn[] = historyMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Abort controller for the stream
      abortControllerRef.current = new AbortController();

      try {
        let detectedLang = selectedLanguage === 'auto' ? (detectedLanguage || null) : selectedLanguage;
        let responseLang = 'en';

        await streamChatMessage(
          {
            message: trimmed,
            language: selectedLanguage === 'auto' ? (detectedLanguage || null) : selectedLanguage,
            conversation,
          },
          {
            onMeta: (meta) => {
              responseLang = meta.language;
              // Update the assistant message with correct language + sources
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === loadingId
                    ? { ...m, language: meta.language, sources: meta.sources }
                    : m
                )
              );
            },
            onThinking: () => {
              // Indic path: internal English generation running
              setStatus('thinking');
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === loadingId
                    ? { ...m, content: '', isLoading: true }
                    : m
                )
              );
            },
            onTranslating: () => {
              // Indic path: translation starting — keep loading state, tokens coming next
              setStatus('thinking');
            },
            onToken: (token) => {
              // First token: switch status to indicate response is streaming
              setStatus('idle');
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === loadingId
                    ? { ...m, content: m.content + token, isLoading: false }
                    : m
                )
              );
            },
            onDone: () => {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === loadingId
                    ? { ...m, isLoading: false }
                    : m
                )
              );
              setStatus('idle');
              setIsLLMAvailable(true);
            },
            onError: (detail) => {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === loadingId
                    ? { ...m, content: `⚠️ ${detail}`, isLoading: false }
                    : m
                )
              );
              setStatus('error');
              setIsLLMAvailable(false);
            },
          },
          abortControllerRef.current.signal,
        );
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') {
          // User aborted — leave message as-is
          return;
        }
        const errorText =
          err instanceof Error
            ? err.message
            : 'The AI service is currently unavailable. Please try again.';

        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingId
              ? { ...m, content: `⚠️ ${errorText}`, isLoading: false }
              : m
          )
        );
        setStatus('error');
        setIsLLMAvailable(false);
      } finally {
        isProcessing.current = false;
      }
    },
    [messages, selectedLanguage, ensureHealthChecked],
  );

  const clearConversation = useCallback(() => {
    abortControllerRef.current?.abort();
    setMessages([]);
    setStatus('idle');
  }, []);

  return {
    messages,
    status,
    selectedLanguage,
    setSelectedLanguage,
    sendMessage,
    isLLMAvailable,
    clearConversation,
  };
}
