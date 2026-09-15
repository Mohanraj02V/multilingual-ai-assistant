import React, { useCallback } from 'react';
import { useTextToSpeech } from '../hooks/useTextToSpeech';

interface AudioPlayerProps {
  text: string;
  language?: string;
  className?: string;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
  text,
  language = 'en',
  className = '',
}) => {
  const { status, isAvailable, speak, pause, resume, stop } = useTextToSpeech();

  const handlePlay = useCallback(() => {
    speak(text, language);
  }, [speak, text, language]);

  if (!isAvailable) {
    return (
      <span
        className={`text-xs text-surface-100/30 select-none ${className}`}
        aria-label="Text-to-speech is not available in this browser"
      >
        🔇 TTS unavailable
      </span>
    );
  }

  const isPlaying = status === 'playing';
  const isPaused = status === 'paused';
  const isActive = isPlaying || isPaused;

  return (
    <div className={`flex items-center gap-1.5 ${className}`} role="group" aria-label="Audio playback controls">
      {!isActive ? (
        <button
          id={`play-btn-${text.slice(0, 8).replace(/\s+/g, '-')}`}
          onClick={handlePlay}
          aria-label="Play response audio"
          title="Listen to response"
          className="flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300 transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-900 rounded-sm px-1 py-0.5"
        >
          <SpeakerIcon />
          <span>Listen</span>
        </button>
      ) : (
        <div className="flex items-center gap-1">
          {isPlaying && (
            <button
              onClick={pause}
              aria-label="Pause audio"
              title="Pause"
              className="p-1 text-brand-400 hover:text-brand-300 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 rounded-sm"
            >
              <PauseIcon />
            </button>
          )}
          {isPaused && (
            <button
              onClick={resume}
              aria-label="Resume audio"
              title="Resume"
              className="p-1 text-brand-400 hover:text-brand-300 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 rounded-sm"
            >
              <PlayIcon />
            </button>
          )}
          <button
            onClick={stop}
            aria-label="Stop audio"
            title="Stop"
            className="p-1 text-brand-400 hover:text-red-400 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 rounded-sm"
          >
            <StopIcon />
          </button>
          {isPlaying && (
            <span className="flex gap-0.5 items-end h-3 ml-1" aria-hidden="true">
              <span className="w-0.5 bg-brand-400 animate-[thinking_1.4s_ease-in-out_infinite] h-2" style={{ animationDelay: '0ms' }} />
              <span className="w-0.5 bg-brand-400 animate-[thinking_1.4s_ease-in-out_infinite] h-3" style={{ animationDelay: '200ms' }} />
              <span className="w-0.5 bg-brand-400 animate-[thinking_1.4s_ease-in-out_infinite] h-1.5" style={{ animationDelay: '400ms' }} />
            </span>
          )}
        </div>
      )}
    </div>
  );
};

// ---- SVG Icons ----

const SpeakerIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 0 1 0 7.072M12 6l-4 4H4v4h4l4 4V6zm6.364.636a9 9 0 0 1 0 12.728" />
  </svg>
);

const PauseIcon = () => (
  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <rect x="6" y="5" width="4" height="14" rx="1" />
    <rect x="14" y="5" width="4" height="14" rx="1" />
  </svg>
);

const PlayIcon = () => (
  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M8 5v14l11-7z" />
  </svg>
);

const StopIcon = () => (
  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <rect x="5" y="5" width="14" height="14" rx="2" />
  </svg>
);
