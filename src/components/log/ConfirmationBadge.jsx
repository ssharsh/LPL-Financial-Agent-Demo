// Tiny status pill showing whether an answer has been flagged for advisor
// confirmation. Used inside the transcript log entries.
export default function ConfirmationBadge({ status }) {
  if (status === "requested") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-brand/10 px-2 py-0.5 text-[10px] font-medium text-brand-dark">
        <span aria-hidden="true">✓</span> Flagged for review
      </span>
    );
  }
  return null;
}
