import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";
import TypingIndicator from "./TypingIndicator.jsx";
import ChatInput from "./ChatInput.jsx";
import SuggestedPrompts from "./SuggestedPrompts.jsx";

// The chat thread. Conversation state (messages, isTyping) lives in App.jsx and
// is passed in, so other panels (portfolio, transcript log) can read the same
// conversation. This component handles rendering + scroll behavior.
export default function ChatWindow({
  messages,
  isTyping,
  onSend,
  onRequestConfirmation,
}) {
  const bottomRef = useRef(null);

  // Auto-scroll to the newest message / typing indicator.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* Scrolling message area */}
      <div
        className="flex-1 space-y-4 overflow-y-auto p-4"
        role="log"
        aria-live="polite"
        aria-label="Conversation with portfolio assistant"
      >
        {isEmpty ? (
          <div className="message-in flex h-full flex-col items-center justify-center gap-5 text-center">
            <div
              className="flex h-14 w-14 select-none items-center justify-center rounded-2xl bg-brand text-sm font-bold tracking-wide text-white shadow-soft"
              aria-hidden="true"
            >
              LPL
            </div>
            <div>
              <h3 className="text-xl font-bold text-brand">
                Ask me about <span className="text-brand-dark">your</span> portfolio
              </h3>
              <p className="mx-auto mt-2 max-w-sm text-sm text-gray-600">
                Explore where your money is invested, how it is allocated, and how
                it has performed — answered straight from your own account data.
              </p>
            </div>
            <SuggestedPrompts onPick={onSend} disabled={isTyping} />
          </div>
        ) : (
          <>
            {messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                onRequestConfirmation={onRequestConfirmation}
              />
            ))}
            {isTyping && <TypingIndicator />}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggested prompts stay available below the thread once chatting starts */}
      {!isEmpty && (
        <div className="border-t border-gray-100 px-4 py-2">
          <SuggestedPrompts onPick={onSend} disabled={isTyping} />
        </div>
      )}

      <ChatInput onSend={onSend} disabled={isTyping} />
    </div>
  );
}
