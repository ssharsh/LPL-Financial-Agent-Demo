// Generic empty-state block for a panel with nothing to show yet.
export default function EmptyState({ title, message }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-1 p-6 text-center">
      <h3 className="text-sm font-semibold text-gray-600">{title}</h3>
      {message && <p className="max-w-xs text-xs text-gray-400">{message}</p>}
    </div>
  );
}
