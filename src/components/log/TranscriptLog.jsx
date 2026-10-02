import ConfirmationBadge from "./ConfirmationBadge.jsx";
import { downloadTranscript } from "../../utils/exportLog.js";
import { formatTime } from "../../utils/format.js";

// Readable, timestamped record of the whole conversation. Clients can flag any
// individual answer for advisor confirmation, and export the full log to send
// to LPL for review.
export default function TranscriptLog({
  messages,
  client,
  onRequestConfirmation,
}) {
  const flaggedCount = messages.filter(
    (m) => m.role === "assistant" && m.confirmation === "requested"
  ).length;

  const hasMessages = messages.length > 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-gray-700">Conversation Log</h2>
        <button
          type="button"
          onClick={() => downloadTranscript(messages, client)}
          disabled={!hasMessages}
          className="rounded-md border border-brand/40 bg-white px-2 py-1 text-[11px] font-medium text-brand shadow-sm transition hover:border-brand hover:bg-brand/5 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Export log
        </button>
      </div>

      {flaggedCount > 0 && (
        <div className="flex items-center gap-1.5 border-b border-brand/10 bg-brand/5 px-4 py-2 text-[11px] font-medium text-brand-dark">
          <span aria-hidden="true">✓</span>
          <span>
            {flaggedCount} answer{flaggedCount > 1 ? "s" : ""} flagged for LPL
            advisor review.
          </span>
        </div>
      )}

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {!hasMessages ? (
          <p className="text-center text-xs text-gray-500">
            Your conversation will be logged here. You can flag any answer for
            advisor confirmation and export the full log for LPL to review.
          </p>
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              className="rounded-lg border border-gray-100 bg-white p-2.5 text-[11px] shadow-sm"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`font-semibold ${
                    m.role === "user" ? "text-gray-800" : "text-brand"
                  }`}
                >
                  {m.role === "user" ? "You" : "Assistant"}
                </span>
                <span className="text-gray-500">{formatTime(m.createdAt)}</span>
                {m.role === "assistant" && (
                  <ConfirmationBadge status={m.confirmation} />
                )}
              </div>
              <p className="mt-0.5 text-gray-700">{m.text}</p>

              {/* Per-answer flag action, only on grounded assistant answers */}
              {m.role === "assistant" &&
                m.type !== "advice_declined" &&
                m.type !== "unknown" &&
                m.confirmation !== "requested" && (
                  <button
                    type="button"
                    onClick={() => onRequestConfirmation(m.id)}
                    className="mt-1 text-[10px] font-medium text-brand underline-offset-2 transition hover:text-brand-dark hover:underline"
                  >
                    Flag this answer for advisor confirmation
                  </button>
                )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
