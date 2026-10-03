// Clickable starter questions to beat the blank-page problem. Each one maps to
// a backend fact tool (accounts, performance, holdings, transactions); the last
// shows the assistant declining to give advice.
const PROMPTS = [
  "What are my accounts worth?",
  "How did my portfolio perform from October 2024 to September 2026?",
  "What do I hold, by asset class?",
  "Show my deposits and withdrawals in 2026",
  "How did my accounts do in September 2026?",
  "Should I buy more stocks?",
];

export default function SuggestedPrompts({ onPick, disabled }) {
  return (
    <div className="flex flex-wrap gap-2">
      {PROMPTS.map((prompt) => (
        <button
          key={prompt}
          type="button"
          onClick={() => onPick(prompt)}
          disabled={disabled}
          className="rounded-full border border-brand/30 bg-white px-3 py-1.5 text-xs font-medium text-brand shadow-sm transition hover:-translate-y-0.5 hover:border-brand hover:bg-brand/5 hover:shadow-soft disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}
