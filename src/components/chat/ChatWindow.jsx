import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";
import TypingIndicator from "./TypingIndicator.jsx";
import ChatInput from "./ChatInput.jsx";

// The chat thread. Conversation state (messages, isTyping) lives in App.jsx and
// is passed in, so other panels (portfolio) can read the same conversation.
// This component handles rendering + scroll behavior.
export default function ChatWindow({
  messages,
  isTyping,
  onSend,
  onScheduleMeeting,
}) {
  const scrollRef = useRef(null);

  // Auto-scroll to the newest message / typing indicator. Scroll only the
  // message container: scrollIntoView would also scroll the page itself and
  // reveal blank space below the layout.
  useEffect(() => {
    const el = scrollRef.current;
    el?.scrollTo?.({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, isTyping]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* Scrolling message area */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto p-4"
        role="log"
        aria-live="polite"
        aria-label="Conversation with portfolio assistant"
      >
        {isEmpty ? (
          <div className="message-in flex h-full flex-col items-center justify-center gap-5 text-center">
            <div
              className="flex h-14 w-14 select-none items-center justify-center rounded-2xl bg-brand text-xs font-bold tracking-wide text-white shadow-soft"
              aria-hidden="true"
            >
              Orama
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
          </div>
        ) : (
          <>
            {messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                onScheduleMeeting={onScheduleMeeting}
              />
            ))}
            {isTyping && <TypingIndicator />}
          </>
        )}
      </div>

      <ChatInput onSend={onSend} disabled={isTyping} />
    </div>
  );
}
