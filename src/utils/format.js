// Small formatting helpers used across the UI.

export function formatCurrency(value, { compact = false } = {}) {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: compact ? 1 : 2,
  }).format(value);
}

export function formatPercent(value, { signed = false } = {}) {
  if (value == null || Number.isNaN(value)) return "—";
  const formatted = new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  }).format(value / 100);
  if (signed && value > 0) return `+${formatted}`;
  return formatted;
}

export function formatSignedCurrency(value) {
  if (value == null || Number.isNaN(value)) return "—";
  const base = formatCurrency(Math.abs(value));
  return value < 0 ? `-${base}` : `+${base}`;
}

// Parse an ISO string. Date-only strings (YYYY-MM-DD) are treated as local
// time so they don't shift a day due to UTC parsing.
function parseDate(isoString) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(isoString)) {
    const [y, m, d] = isoString.split("-").map(Number);
    return new Date(y, m - 1, d);
  }
  return new Date(isoString);
}

// Human-readable date, e.g. "Oct 2, 2026".
export function formatDate(isoString) {
  if (!isoString) return "—";
  return parseDate(isoString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// Timestamp for transcript/log entries, e.g. "10:42 AM".
export function formatTime(isoString) {
  if (!isoString) return "—";
  return new Date(isoString).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}
