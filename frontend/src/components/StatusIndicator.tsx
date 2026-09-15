import React from 'react';
import type { AppStatus } from '../types';

interface StatusIndicatorProps {
  status: AppStatus;
  isLLMAvailable: boolean | null;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  isLLMAvailable,
}) => {
  const { dot, label } = getStatusDisplay(status, isLLMAvailable);

  return (
    <div
      className="flex items-center gap-1.5"
      role="status"
      aria-live="polite"
      aria-label={`Assistant status: ${label}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot}`}
        aria-hidden="true"
      />
      <span className="text-xs text-white/40 font-medium">{label}</span>
    </div>
  );
};

function getStatusDisplay(
  status: AppStatus,
  isLLMAvailable: boolean | null,
): { dot: string; label: string } {
  switch (status) {
    case 'listening':
      return { dot: 'bg-red-400 animate-pulse', label: 'Listening...' };
    case 'transcribing':
      return { dot: 'bg-amber-400 animate-pulse', label: 'Transcribing...' };
    case 'thinking':
      return { dot: 'bg-brand-400 animate-pulse', label: 'Thinking...' };
    case 'speaking':
      return { dot: 'bg-emerald-400 animate-pulse', label: 'Speaking...' };
    case 'error':
      return { dot: 'bg-red-500', label: 'Error' };
    default:
      if (isLLMAvailable === false) {
        return { dot: 'bg-red-500', label: 'AI Offline' };
      }
      return { dot: 'bg-emerald-400', label: 'Online' };
  }
}
