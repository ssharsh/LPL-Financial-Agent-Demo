// Inline error block with an optional retry action.
export default function ErrorState({ message, onRetry }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800 shadow-soft"
    >
      <span aria-hidden="true">⚠️</span>
      <div className="flex-1">
        <p>{message || "Something went wrong. Please try again."}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-1 font-semibold text-red-900 underline underline-offset-2 transition hover:text-red-700"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
