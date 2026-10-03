import { downloadTranscript } from "../../utils/exportLog.js";
import { formatTime } from "../../utils/format.js";

// Readable, timestamped record of the whole conversation, exportable as text.
export default function TranscriptLog({ messages, client }) {
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
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {!hasMessages ? (
          <p className="text-center text-xs text-gray-500">
            Your conversation will be logged here. You can export the full log at any time.
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
                {m.meetingRequested && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-brand/10 px-2 py-0.5 text-[10px] font-medium text-brand-dark">
                    ✓ Meeting requested
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-gray-700">{m.text}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
