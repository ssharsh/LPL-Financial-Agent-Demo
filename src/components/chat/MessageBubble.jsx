import { formatTime } from "../../utils/format.js";
import ChartRenderer from "./ChartRenderer.jsx";

// The model sometimes uses **bold** markdown; show it as bold instead of
// literal asterisks. Everything else stays plain text (no HTML injection).
function renderBold(text) {
  return String(text ?? "")
    .split(/(\*\*[^*\n]+\*\*)/g)
    .map((part, i) =>
      /^\*\*[^*\n]+\*\*$/.test(part) ? <strong key={i}>{part.slice(2, -2)}</strong> : part
    );
}

// Renders one chat message. User messages are simple right-aligned bubbles.
// Assistant messages show the grounded answer, the "Based on:" citations that
// back it up, and a button to flag the answer for advisor confirmation.
export default function MessageBubble({ message, onRequestConfirmation }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="message-in flex items-end justify-end gap-2">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-brand px-4 py-2 text-sm text-white shadow-soft">
          <p className="whitespace-pre-wrap">{message.text}</p>
          <p className="mt-1 text-right text-[10px] text-white/80">
            {formatTime(message.createdAt)}
          </p>
        </div>
        {/* Decorative user avatar */}
        <div
          className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full bg-gray-200 text-[11px] font-semibold text-gray-600"
          aria-hidden="true"
        >
          You
        </div>
      </div>
    );
  }

  const declined = message.type === "advice_declined";
  const unknown = message.type === "unknown";

  return (
    <div className="message-in flex items-start justify-start gap-2">
      {/* Decorative brand-green assistant avatar */}
      <div
        className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full bg-brand text-[10px] font-bold tracking-wide text-white shadow-soft"
        aria-hidden="true"
      >
        LPL
      </div>
      {/* Charts have no intrinsic width, so a bubble with one takes the full column */}
      <div className={`max-w-[85%] space-y-2 ${message.chart ? "w-full" : ""}`}>
        <div
          className={[
            "rounded-2xl rounded-bl-sm px-4 py-3 text-sm shadow-soft",
            declined
              ? "border border-amber-300 bg-amber-50 text-amber-900"
              : "border border-gray-200 bg-white text-gray-800",
          ].join(" ")}
        >
          {declined && (
            <p className="mb-1 flex items-center gap-1 text-xs font-semibold text-amber-800">
              <span aria-hidden="true">⚠️</span> Not financial advice
            </p>
          )}
          {message.interpretation && (
            <p className="mb-1 text-xs italic text-gray-500">{message.interpretation}</p>
          )}
          <p className="whitespace-pre-wrap">{renderBold(message.text)}</p>

          {/* Inline chart built by the backend from this answer's tool results */}
          {message.chart && (
            <div className="mt-3 border-t border-gray-200 pt-3">
              <ChartRenderer chart={message.chart} />
            </div>
          )}

          {/* Citations: show exactly which portfolio data backs the answer */}
          {message.citations?.length > 0 && (
            <div className="mt-3 border-t border-gray-200 pt-2">
              <p className="mb-1.5 inline-flex items-center gap-1.5 rounded-full bg-brand/10 px-2 py-0.5 text-[11px] font-semibold text-brand-dark">
                <span aria-hidden="true">🛡️</span>
                <span>Grounded in your portfolio data</span>
              </p>
              <ul className="space-y-0.5">
                {message.citations.map((c, i) => (
                  <li key={i} className="flex justify-between gap-3 text-[11px] text-gray-600">
                    <span className="font-medium">{c.label}</span>
                    <span className="text-right text-gray-500">{c.detail}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer: timestamp + flag-for-confirmation (only on grounded answers) */}
        <div className="flex items-center gap-3 px-1">
          <span className="text-[10px] text-gray-500">{formatTime(message.createdAt)}</span>
          {message.logId && (
            <span className="text-[10px] text-gray-500">Log {message.logId}</span>
          )}
          {!declined && !unknown && (
            message.confirmation === "requested" ? (
              <span className="flex items-center gap-1 text-[10px] font-medium text-brand">
                <span aria-hidden="true">✓</span> Sent to LPL for advisor review
              </span>
            ) : (
              <button
                type="button"
                onClick={() => onRequestConfirmation(message.id)}
                className="rounded-full border border-brand/30 px-2 py-0.5 text-[10px] font-medium text-brand transition hover:bg-brand/10 hover:text-brand-dark"
              >
                Request advisor confirmation
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
}
