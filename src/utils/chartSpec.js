// Pure helpers that turn a backend chart spec into something Recharts can draw.
//
// Backend spec (envelope `chart`, and /api/portfolio `charts.*`):
//   { type, x, y, series, rows }
//   - type: line | stacked_area | bar | pie | table
//   - x / y: row keys for the category axis and the numeric value
//   - series: "" for one series, else the row key to group by (long format)
//   - rows: the tool's rows; numbers arrive as exact strings ("142921.25")
// Anything malformed normalizes to null so the UI renders nothing, not a crash.
import { formatCurrency, formatDate, formatPercent } from "./format.js";

export const CHART_TYPES = ["line", "stacked_area", "bar", "pie", "table"];

export const PALETTE = [
  "#0b5c3f",
  "#13a06b",
  "#2f8fd6",
  "#c98a1b",
  "#7b61a6",
  "#9aa5b1",
  "#d0573b",
  "#4bb3a8",
];

const isPlainObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

// Validate + reshape a spec. Returns null when it cannot be drawn.
//   table  -> { type, columns, rows }
//   others -> { type, x, y, seriesKeys, data }  (data is wide: one key per series)
export function normalizeChart(spec) {
  if (!isPlainObject(spec) || !CHART_TYPES.includes(spec.type)) return null;
  const { type, x, y, series } = spec;
  const rows = Array.isArray(spec.rows) ? spec.rows.filter(isPlainObject) : [];
  if (rows.length === 0) return null;

  if (type === "table") {
    const columns = Object.keys(rows[0]);
    return columns.length ? { type, columns, rows } : null;
  }

  if (typeof x !== "string" || typeof y !== "string") return null;
  if (!(x in rows[0]) || !(y in rows[0])) return null;

  const valid = rows
    .map((r) => ({ ...r, [y]: toNumber(r[y]) }))
    .filter((r) => Number.isFinite(r[y]));
  if (valid.length === 0) return null;

  const grouped = typeof series === "string" && series !== "" && series in rows[0];
  if (!grouped) {
    return { type, x, y, seriesKeys: [y], data: valid.map((r) => ({ [x]: r[x], [y]: r[y] })) };
  }

  // Long -> wide: one output row per x value (first-seen order), one key per series value.
  const seriesKeys = [];
  const byX = new Map();
  for (const r of valid) {
    const s = String(r[series]);
    if (!seriesKeys.includes(s)) seriesKeys.push(s);
    if (!byX.has(r[x])) byX.set(r[x], { [x]: r[x] });
    byX.get(r[x])[s] = r[y];
  }
  return { type, x, y, seriesKeys, data: [...byX.values()] };
}

function toNumber(v) {
  if (typeof v === "number") return v;
  if (typeof v === "string" && v.trim() !== "") return Number(v);
  return NaN;
}

// What kind of number a row key holds, guessed from its name.
export function valueKind(key) {
  const k = String(key ?? "");
  if (/_pct$|percent|return/i.test(k)) return "percent";
  if (/value|amount|cash|flow|gain|price|balance/i.test(k)) return "currency";
  return "number";
}

export function formatValue(kind, value, { compact = false } = {}) {
  const n = toNumber(value);
  if (!Number.isFinite(n)) return "—";
  if (kind === "currency") return formatCurrency(n, { compact });
  if (kind === "percent") return formatPercent(n);
  return n.toLocaleString("en-US");
}

// Category labels: "2024-10" -> "Oct 2024" (no timezone shift), "roth_ira" -> "Roth ira".
export function formatCategory(value) {
  if (value == null) return "";
  const s = String(value);
  if (/^\d{4}-\d{2}$/.test(s) || /^\d{4}-\d{2}-\d{2}$/.test(s)) return formatDate(s);
  if (/^[a-z0-9_]+$/.test(s)) return humanizeKey(s);
  return s;
}

// "end_value" -> "End value"
export function humanizeKey(key) {
  const s = String(key ?? "").replace(/_/g, " ").trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
}

// Short accessible description, e.g. "Line chart of End value by Month".
export function describeChart(spec) {
  const names = {
    line: "Line chart",
    stacked_area: "Stacked area chart",
    bar: "Bar chart",
    pie: "Pie chart",
    table: "Table",
  };
  if (!spec) return "";
  if (spec.type === "table") return `Table with columns ${spec.columns.map(humanizeKey).join(", ")}`;
  return `${names[spec.type]} of ${humanizeKey(spec.y)} by ${humanizeKey(spec.x)}`;
}
