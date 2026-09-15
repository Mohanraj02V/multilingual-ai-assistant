import React, { useState, useRef, useCallback, useEffect } from 'react';
import { MicrophoneButton } from './MicrophoneButton';
import { useSpeechToText } from '../hooks/useSpeechToText';
import type { AppStatus } from '../types';

interface MessageInputProps {
  onSend: (message: string) => void;
  status: AppStatus;
  selectedLanguage: string;
  disabled?: boolean;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSend,
  status,
  selectedLanguage,
  disabled = false,
}) => {
  const [inputValue, setInputValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isThinking = status === 'thinking';

  const handleFinalTranscript = useCallback(
    (transcript: string) => {
      setInputValue(transcript);
      // Auto-submit after a short delay so the user can see the transcription
      setTimeout(() => {
        if (transcript.trim()) {
          onSend(transcript.trim());
          setInputValue('');
        }
      }, 400);
    },
    [onSend],
  );

  const {
    status: sttStatus,
    interimTranscript,
    isAvailable: sttAvailable,
    startListening,
    stopListening,
    error: sttError,
  } = useSpeechToText(handleFinalTranscript);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [inputValue]);

  const handleSend = useCallback(() => {
    const msg = inputValue.trim();
    if (!msg || isThinking) return;
    onSend(msg);
    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [inputValue, isThinking, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const displayValue = interimTranscript || inputValue;
  const canSend = displayValue.trim().length > 0 && !isThinking && !disabled;
  const isListening = sttStatus === 'listening';

  return (
    <div className="flex-shrink-0 border-t border-white/5 bg-surface-900/80 backdrop-blur-sm">
      {/* STT error banner */}
      {sttError && (
        <div
          role="alert"
          className="px-4 py-2 text-xs text-amber-400 bg-amber-400/5 border-b border-amber-400/10"
        >
          {sttError}
        </div>
      )}

      {/* Interim transcript preview */}
      {interimTranscript && (
        <div
          className="px-4 py-2 text-xs text-white/40 italic border-b border-white/5"
          aria-live="polite"
          aria-label="Interim transcription"
        >
          🎙 {interimTranscript}
        </div>
      )}

      {/* Input row */}
      <div className="flex items-end gap-2 px-4 py-3">
        {/* Microphone button */}
        <MicrophoneButton
          status={sttStatus}
          isAvailable={sttAvailable}
          onStart={() => startListening(selectedLanguage)}
          onStop={stopListening}
          disabled={isThinking || disabled}
        />

        {/* Text area */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            id="message-input"
            value={displayValue}
            onChange={(e) => !isListening && setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isListening ? 'Listening...' : 'Type your message... (Enter to send, Shift+Enter for new line)'}
            disabled={disabled || isThinking}
            rows={1}
            maxLength={2000}
            aria-label="Message input"
            aria-multiline="true"
            className={`
              w-full resize-none rounded-2xl bg-surface-800 border border-white/8
              text-sm text-white placeholder-white/25
              px-4 py-2.5 pr-12
              transition-all duration-150
              focus:outline-none focus:border-brand-500/50 focus:bg-surface-750
              focus-visible:ring-1 focus-visible:ring-brand-500/30
              disabled:opacity-40 disabled:cursor-not-allowed
              scrollbar-thin scrollbar-thumb-white/10
              ${isListening ? 'border-red-500/30 bg-red-500/5' : ''}
            `}
            style={{ minHeight: '44px', maxHeight: '160px' }}
          />
        </div>

        {/* Send button */}
        <button
          id="send-button"
          type="button"
          onClick={handleSend}
          disabled={!canSend}
          aria-label="Send message"
          title="Send message"
          className={`
            flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center
            transition-all duration-200
            focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-900
            ${canSend
              ? 'bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-900/40'
              : 'bg-surface-800 text-white/20 cursor-not-allowed border border-white/5'
            }
          `}
        >
          {isThinking ? <ThinkingSpinner /> : <SendIcon />}
        </button>
      </div>
    </div>
  );
};

// ---- Icons ----

const SendIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
  </svg>
);

const ThinkingSpinner = () => (
  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z" />
  </svg>
);
