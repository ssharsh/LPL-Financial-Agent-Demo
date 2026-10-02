import { LineChart, Line, ResponsiveContainer } from "recharts";
import {
  formatCurrency,
  formatPercent,
  formatSignedCurrency,
  formatDate,
} from "../../utils/format.js";

// Turns an assistant message's grounded `data` payload into a small, legible
// inline visualization that sits inside the chat bubble. Rendered only when the
// message actually carries data — advice_declined/unknown/empty pass data=null
// and fall back to plain text (we return null here for those).
//
// data.kind is one of: summary | allocation | sectors | holdings | performance
//                      | activity
export default function MessageData({ data }) {
  if (!data) return null;

  switch (data.kind) {
    case "summary":
      return <SummaryBlock summary={data.summary} />;
    case "allocation":
      return (
        <BarList
          items={toBars(data.allocation, { label: "name", perItemColor: true })}
          max={5}
        />
      );
    case "sectors":
      return <BarList items={toBars(data.sectors, { label: "name" })} max={5} />;
    case "holdings":
      return <HoldingsBars holdings={data.holdings} />;
    case "performance":
      return <PerformanceSparkline performance={data.performance} />;
    case "activity":
      return <ActivityList activity={data.recentActivity} />;
    default:
      return null;
  }
}

// --- helpers ---------------------------------------------------------------

// Normalize an array into { name, percent, color } bar rows sorted by percent
// desc. Brand green is the default bar color; allocation rows keep their own.
function toBars(items, { label, perItemColor = false } = {}) {
  return [...items]
    .sort((a, b) => b.percent - a.percent)
    .map((item) => ({
      name: item[label],
      percent: item.percent,
      color: perItemColor && item.color ? item.color : "#0b5c3f",
    }));
}

// Horizontal percent-bar list used for allocation and sectors.
function BarList({ items, max = 5 }) {
  const rows = items.slice(0, max);
  const scaleMax = Math.max(...rows.map((r) => r.percent), 1);
  return (
    <ul className="space-y-1.5">
      {rows.map((row) => (
        <li key={row.name} className="text-[11px]">
          <div className="mb-0.5 flex items-center justify-between gap-2">
            <span className="truncate text-gray-700">{row.name}</span>
            <span className="font-medium tabular-nums text-gray-600">
              {formatPercent(row.percent)}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full rounded-full"
              style={{
                width: `${(row.percent / scaleMax) * 100}%`,
                backgroundColor: row.color,
              }}
              aria-hidden="true"
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

// Top holdings as brand-green bars with ticker, value and percent.
function HoldingsBars({ holdings }) {
  const rows = [...holdings]
    .sort((a, b) => b.percent - a.percent)
    .slice(0, 5);
  const scaleMax = Math.max(...rows.map((h) => h.percent), 1);
  return (
    <ul className="space-y-1.5">
      {rows.map((h) => (
        <li key={h.ticker} className="text-[11px]">
          <div className="mb-0.5 flex items-center justify-between gap-2">
            <span className="font-semibold text-gray-700">{h.ticker}</span>
            <span className="tabular-nums text-gray-600">
              {formatCurrency(h.value)}{" "}
              <span className="font-medium text-gray-500">
                · {formatPercent(h.percent)}
              </span>
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full rounded-full bg-brand"
              style={{ width: `${(h.percent / scaleMax) * 100}%` }}
              aria-hidden="true"
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

// A tidy stat block for the summary payload.
function SummaryBlock({ summary }) {
  const dayUp = summary.dayChangeValue >= 0;
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[11px]">
      <Stat label="Total value" value={formatCurrency(summary.totalValue)} />
      <Stat
        label="Today's change"
        value={`${formatSignedCurrency(summary.dayChangeValue)} (${formatPercent(summary.dayChangePercent, { signed: true })})`}
        tone={dayUp ? "up" : "down"}
      />
      <Stat
        label="All-time gain"
        value={`${formatSignedCurrency(summary.totalGainValue)} (${formatPercent(summary.totalGainPercent, { signed: true })})`}
        tone={summary.totalGainValue >= 0 ? "up" : "down"}
      />
      <Stat label="Cash available" value={formatCurrency(summary.cashAvailable)} />
    </dl>
  );
}

function Stat({ label, value, tone }) {
  const toneClass =
    tone === "up"
      ? "text-brand"
      : tone === "down"
        ? "text-red-600"
        : "text-gray-800";
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wide text-gray-500">{label}</dt>
      <dd className={`font-semibold tabular-nums ${toneClass}`}>{value}</dd>
    </div>
  );
}

// Mini sparkline of portfolio value with a first->last change caption.
function PerformanceSparkline({ performance }) {
  const first = performance[0];
  const last = performance[performance.length - 1];
  const change = last.value - first.value;
  const changePct = (change / first.value) * 100;
  const up = change >= 0;
  return (
    <div>
      <div className="h-24">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={performance} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
            <Line
              type="monotone"
              dataKey="value"
              stroke="#0b5c3f"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-[11px] text-gray-600">
        <span className={`font-semibold tabular-nums ${up ? "text-brand" : "text-red-600"}`}>
          {formatSignedCurrency(change)} ({formatPercent(changePct, { signed: true })})
        </span>{" "}
        over 12 months
      </p>
    </div>
  );
}

// Compact list of recent account activity.
function ActivityList({ activity }) {
  return (
    <ul className="space-y-1.5">
      {activity.map((a, i) => (
        <li key={i} className="flex items-start justify-between gap-3 text-[11px]">
          <span className="min-w-0">
            <span className="block text-gray-700">{a.description}</span>
            <span className="text-[10px] text-gray-500">{formatDate(a.date)}</span>
          </span>
          <span
            className={`shrink-0 font-medium tabular-nums ${a.amount >= 0 ? "text-brand" : "text-red-600"}`}
          >
            {formatSignedCurrency(a.amount)}
          </span>
        </li>
      ))}
    </ul>
  );
}
