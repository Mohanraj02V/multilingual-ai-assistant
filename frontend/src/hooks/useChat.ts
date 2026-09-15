import { useState, useCallback, useRef } from 'react';
import { sendChatMessage, checkHealth } from '../services/api';
import type {
  Message,
  AppStatus,
  ConversationTurn,
  ChatResponse,
} from '../types';

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

interface UseChatReturn {
  messages: Message[];
  status: AppStatus;
  selectedLanguage: string;
  setSelectedLanguage: (lang: string) => void;
  sendMessage: (content: string) => Promise<void>;
  isLLMAvailable: boolean | null;
  clearConversation: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<AppStatus>('idle');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('auto');
  const [isLLMAvailable, setIsLLMAvailable] = useState<boolean | null>(null);
  const isProcessing = useRef(false);

  // Check LLM health on first send (lazy)
  const ensureHealthChecked = useCallback(async () => {
    if (isLLMAvailable !== null) return;
    try {
      const health = await checkHealth();
      setIsLLMAvailable(health.llm_available);
    } catch {
      setIsLLMAvailable(false);
    }
  }, [isLLMAvailable]);

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || isProcessing.current) return;

      isProcessing.current = true;
      await ensureHealthChecked();

      // Add user message
      const userMessage: Message = {
        id: generateId(),
        role: 'user',
        content: trimmed,
        language: selectedLanguage === 'auto' ? 'en' : selectedLanguage,
        timestamp: new Date(),
      };

      // Add loading placeholder for assistant
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

      try {
        const response: ChatResponse = await sendChatMessage({
          message: trimmed,
          language: selectedLanguage === 'auto' ? null : selectedLanguage,
          conversation,
        });

        const assistantMessage: Message = {
          id: loadingId,
          role: 'assistant',
          content: response.answer,
          language: response.language ?? 'en',
          timestamp: new Date(),
          sources: response.sources,
          isLoading: false,
        };

        setMessages((prev) =>
          prev.map((m) => (m.id === loadingId ? assistantMessage : m)),
        );
        setStatus('idle');
        setIsLLMAvailable(true);
      } catch (err: unknown) {
        const errorText =
          err instanceof Error
            ? err.message
            : 'The AI service is currently unavailable. Please try again.';

        const errorMessage: Message = {
          id: loadingId,
          role: 'assistant',
          content: `⚠️ ${errorText}`,
          language: 'en',
          timestamp: new Date(),
          isLoading: false,
        };

        setMessages((prev) =>
          prev.map((m) => (m.id === loadingId ? errorMessage : m)),
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
