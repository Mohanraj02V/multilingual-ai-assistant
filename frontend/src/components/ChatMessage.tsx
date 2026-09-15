import React from 'react';
import { AudioPlayer } from './AudioPlayer';
import type { Message } from '../types';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const isLoading = message.isLoading;

  if (isLoading) {
    return (
      <div className="flex items-start gap-3 animate-fade-in">
        <AssistantAvatar />
        <div className="flex flex-col gap-1.5 max-w-[75%]">
          <div className="bg-surface-800 rounded-2xl rounded-tl-sm px-4 py-3 border border-white/5">
            <ThinkingDots />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex items-start gap-3 animate-fade-in ${isUser ? 'flex-row-reverse' : ''}`}
      role="article"
      aria-label={`${isUser ? 'Your' : 'Assistant'} message`}
    >
      {/* Avatar */}
      {isUser ? <UserAvatar /> : <AssistantAvatar />}

      {/* Bubble */}
      <div className={`flex flex-col gap-1.5 max-w-[75%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`
            relative rounded-2xl px-4 py-3 text-sm leading-relaxed break-words
            ${isUser
              ? 'bg-brand-600 text-white rounded-tr-sm'
              : 'bg-surface-800 text-surface-50 rounded-tl-sm border border-white/5'
            }
          `}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Footer: timestamp + sources + audio */}
        <div className={`flex items-center gap-2 flex-wrap ${isUser ? 'flex-row-reverse' : ''}`}>
          <time
            className="text-[10px] text-white/25 tabular-nums"
            dateTime={message.timestamp.toISOString()}
          >
            {formatTime(message.timestamp)}
          </time>

          {!isUser && message.sources && message.sources.length > 0 && (
            <span className="text-[10px] text-white/25">
              · from {message.sources.map((s) => s.title).join(', ')}
            </span>
          )}

          {!isUser && (
            <AudioPlayer
              text={message.content}
              language={message.language}
              className="ml-0.5"
            />
          )}
        </div>
      </div>
    </div>
  );
};

// ---- Subcomponents ----

const AssistantAvatar = () => (
  <div
    className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-900/50"
    aria-hidden="true"
  >
    <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.3 24.3 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23-.693L5 14.5m14.8.8 1.402 1.402c1 1 .03 2.798-1.414 2.798H4.212c-1.444 0-2.414-1.798-1.414-2.798L4.2 15.3" />
    </svg>
  </div>
);

const UserAvatar = () => (
  <div
    className="flex-shrink-0 w-8 h-8 rounded-full bg-surface-700 border border-white/10 flex items-center justify-center"
    aria-hidden="true"
  >
    <svg className="w-4 h-4 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
    </svg>
  </div>
);

const ThinkingDots = () => (
  <div className="flex items-center gap-1.5 h-5" aria-label="Thinking..." role="status">
    {[0, 200, 400].map((delay) => (
      <span
        key={delay}
        className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-[thinking_1.4s_ease-in-out_infinite]"
        style={{ animationDelay: `${delay}ms` }}
        aria-hidden="true"
      />
    ))}
  </div>
);

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
