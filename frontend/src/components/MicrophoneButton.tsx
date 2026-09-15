import React from 'react';
import type { STTStatus } from '../types';

interface MicrophoneButtonProps {
  status: STTStatus;
  isAvailable: boolean;
  onStart: () => void;
  onStop: () => void;
  disabled?: boolean;
}

export const MicrophoneButton: React.FC<MicrophoneButtonProps> = ({
  status,
  isAvailable,
  onStart,
  onStop,
  disabled = false,
}) => {
  const isListening = status === 'listening';
  const isTranscribing = status === 'transcribing';
  const isActive = isListening || isTranscribing;

  const handleClick = () => {
    if (disabled || !isAvailable) return;
    if (isActive) {
      onStop();
    } else {
      onStart();
    }
  };

  const getAriaLabel = () => {
    if (!isAvailable) return 'Voice input not available in this browser';
    if (isListening) return 'Stop voice input';
    if (isTranscribing) return 'Transcribing...';
    return 'Start voice input';
  };

  const getTitle = () => {
    if (!isAvailable) return 'Voice input not supported';
    if (isListening) return 'Stop listening';
    return 'Start voice input';
  };

  return (
    <button
      id="microphone-button"
      type="button"
      onClick={handleClick}
      disabled={disabled || !isAvailable}
      aria-label={getAriaLabel()}
      title={getTitle()}
      className={`
        relative flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center
        transition-all duration-200
        focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-900
        ${!isAvailable || disabled
          ? 'text-white/20 cursor-not-allowed bg-white/5'
          : isListening
            ? 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-900/40'
            : 'bg-surface-800 hover:bg-surface-700 border border-white/10 text-white/60 hover:text-white/90'
        }
      `}
    >
      {/* Pulsing ring when listening */}
      {isListening && (
        <span
          className="absolute inset-0 rounded-full bg-red-500/40 animate-ping"
          aria-hidden="true"
        />
      )}

      {isListening ? (
        <StopIcon />
      ) : isTranscribing ? (
        <TranscribingSpinner />
      ) : (
        <MicIcon />
      )}
    </button>
  );
};

// ---- Icons ----

const MicIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
  </svg>
);

const StopIcon = () => (
  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <rect x="5" y="5" width="14" height="14" rx="2" />
  </svg>
);

const TranscribingSpinner = () => (
  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z" />
  </svg>
);
