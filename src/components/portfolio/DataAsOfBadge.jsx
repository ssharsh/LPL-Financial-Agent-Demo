import { formatDate } from "../../utils/format.js";

// Small trust cue: shows when the data was last updated so clients know the
// numbers are a snapshot, plus a short "not advice" reminder.
export default function DataAsOfBadge({ asOf }) {
  return (
    <div className="flex items-center justify-between gap-2 border-t border-gray-200 bg-surface-tint px-4 py-2 text-[11px] text-gray-600">
      <span>Data as of {formatDate(asOf)}</span>
      <span className="font-medium">Not financial advice</span>
    </div>
  );
}
