
import { ChatWindow } from './components/ChatWindow';
import { MessageInput } from './components/MessageInput';
import { LanguageSelector } from './components/LanguageSelector';
import { StatusIndicator } from './components/StatusIndicator';
import { useChat } from './hooks/useChat';

export default function App() {
  const {
    messages,
    status,
    selectedLanguage,
    setSelectedLanguage,
    sendMessage,
    isLLMAvailable,
    clearConversation,
  } = useChat();

  return (
    <div className="h-screen flex flex-col bg-surface-950 text-white antialiased overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-white/5 bg-surface-900/60 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          {/* Logo */}
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-md shadow-brand-900/50" aria-hidden="true">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.3 24.3 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23-.693L5 14.5m14.8.8 1.402 1.402c1 1 .03 2.798-1.414 2.798H4.212c-1.444 0-2.414-1.798-1.414-2.798L4.2 15.3" />
            </svg>
          </div>

          <div>
            <h1 className="text-sm font-semibold text-white leading-none">AI Assistant</h1>
            <StatusIndicator status={status} isLLMAvailable={isLLMAvailable} />
          </div>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-3">
          <LanguageSelector
            value={selectedLanguage}
            onChange={setSelectedLanguage}
          />

          {messages.length > 0 && (
            <button
              id="clear-conversation"
              type="button"
              onClick={clearConversation}
              aria-label="Clear conversation"
              title="Clear conversation"
              className="p-1.5 text-white/30 hover:text-white/70 transition-colors rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            >
              <TrashIcon />
            </button>
          )}
        </div>
      </header>

      {/* Chat area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <ChatWindow
          messages={messages}
          isThinking={status === 'thinking'}
        />
      </main>

      {/* Input area */}
      <footer>
        <MessageInput
          onSend={sendMessage}
          status={status}
          selectedLanguage={selectedLanguage}
          disabled={false}
        />

        {/* Bottom bar */}
        <div className="px-4 pb-2 pt-1 text-center">
          <p className="text-[10px] text-white/15">
            Powered by Ollama · Answers grounded in company knowledge base
          </p>
        </div>
      </footer>
    </div>
  );
}

const TrashIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
  </svg>
);
