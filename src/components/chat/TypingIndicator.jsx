// Animated "assistant is typing" dots shown while a response is pending.
export default function TypingIndicator() {
  return (
    <div
      className="flex items-center gap-1 px-1 py-2"
      role="status"
      aria-label="Assistant is typing"
    >
      <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
      <span className="sr-only">Assistant is typing…</span>
    </div>
  );
}
