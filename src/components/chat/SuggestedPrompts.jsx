// Clickable starter questions to beat the blank-page problem. These map to
// the retrieval engine's handlers so every one returns a grounded answer.
const PROMPTS = [
  "What is my total portfolio value?",
  "Where is my money invested?",
  "How much do I have in technology?",
  "How has my portfolio performed this year?",
  "What are my largest holdings?",
  "How much cash do I have available?",
];

export default function SuggestedPrompts({ onPick, disabled }) {
  return (
    <div className="flex flex-wrap justify-center gap-2">
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
