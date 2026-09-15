import React, { useEffect, useRef } from 'react';
import { ChatMessage } from './ChatMessage';
import type { Message } from '../types';

interface ChatWindowProps {
  messages: Message[];
  isThinking: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ messages, isThinking: _isThinking }) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div
        ref={containerRef}
        className="flex-1 flex flex-col items-center justify-center px-6 select-none"
        aria-label="Chat area — empty"
      >
        <WelcomeScreen />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-6 space-y-5 scroll-smooth"
      role="log"
      aria-label="Conversation"
      aria-live="polite"
    >
      {messages.map((message) => (
        <ChatMessage key={message.id} message={message} />
      ))}
      <div ref={bottomRef} aria-hidden="true" />
    </div>
  );
};

const WelcomeScreen = () => (
  <div className="text-center max-w-sm mx-auto">
    {/* Glowing orb */}
    <div className="relative mx-auto mb-6 w-20 h-20">
      <div className="absolute inset-0 rounded-full bg-brand-500/20 animate-ping" />
      <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-xl shadow-brand-900/50">
        <svg className="w-9 h-9 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.3 24.3 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23-.693L5 14.5m14.8.8 1.402 1.402c1 1 .03 2.798-1.414 2.798H4.212c-1.444 0-2.414-1.798-1.414-2.798L4.2 15.3" />
        </svg>
      </div>
    </div>

    <h2 className="text-xl font-semibold text-white mb-2">How can I help you?</h2>
    <p className="text-sm text-white/40 leading-relaxed mb-6">
      Ask me anything in any language. Type or use the microphone to speak.
    </p>

    {/* Example prompts */}
    <div className="grid gap-2 text-left">
      {[
        'What are your working hours?',
        'What is your refund policy?',
        'How can I contact support?',
      ].map((prompt) => (
        <div
          key={prompt}
          className="text-xs text-white/30 border border-white/5 rounded-xl px-3 py-2 bg-white/2 hover:bg-white/5 transition-colors cursor-default"
        >
          {prompt}
        </div>
      ))}
    </div>
  </div>
);
