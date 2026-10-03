import { Component } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import {
  PALETTE,
  normalizeChart,
  valueKind,
  formatValue,
  formatCategory,
  humanizeKey,
  describeChart,
} from "../../utils/chartSpec.js";

// One generic chart for every backend chart spec {type, x, y, series, rows}.
// Used inline in assistant bubbles and in the portfolio panel. Unknown or
// malformed specs render nothing; a render error also renders nothing.
export default function ChartRenderer({ chart, height = 192 }) {
  const spec = normalizeChart(chart);
  if (!spec) return null;
  return (
    <ChartErrorBoundary>
      {spec.type === "table" ? (
        <TableChart spec={spec} />
      ) : (
        <figure role="img" aria-label={describeChart(spec)} className="m-0">
          {spec.type === "pie" ? (
            <PieSpec spec={spec} height={height} />
          ) : (
            <div style={{ height }}>
              <ResponsiveContainer width="100%" height="100%">
                <CartesianSpec spec={spec} />
              </ResponsiveContainer>
            </div>
          )}
        </figure>
      )}
    </ChartErrorBoundary>
  );
}

class ChartErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

const TICK = { fontSize: 10, fill: "#64748b" };

// line / stacked_area / bar share axes, grid, tooltip and legend.
function CartesianSpec({ spec, ...rest }) {
  const { type, x, y, seriesKeys, data } = spec;
  const kind = valueKind(y);
  const multi = seriesKeys.length > 1;
  const color = (i) => PALETTE[i % PALETTE.length];
  const seriesName = (key) => (multi ? key : humanizeKey(key));

  const common = [
    <CartesianGrid key="grid" strokeDasharray="3 3" stroke="#eef0f2" vertical={false} />,
    <XAxis
      key="x"
      dataKey={x}
      tickFormatter={formatCategory}
      tick={TICK}
      interval="preserveStartEnd"
      minTickGap={16}
    />,
    <YAxis
      key="y"
      tickFormatter={(v) => formatValue(kind, v, { compact: true })}
      tick={TICK}
      width={56}
      domain={type === "line" ? ["auto", "auto"] : [0, "auto"]}
    />,
    <Tooltip
      key="tip"
      formatter={(v, name) => [formatValue(kind, v), name]}
      labelFormatter={formatCategory}
    />,
    multi ? <Legend key="legend" wrapperStyle={{ fontSize: 10 }} /> : null,
  ];
  const margin = { top: 5, right: 8, left: 0, bottom: 0 };

  if (type === "line") {
    return (
      <LineChart data={data} margin={margin} {...rest}>
        {common}
        {seriesKeys.map((k, i) => (
          <Line
            key={k}
            type="monotone"
            dataKey={k}
            name={seriesName(k)}
            stroke={color(i)}
            strokeWidth={2}
            dot={data.length <= 12}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    );
  }
  if (type === "stacked_area") {
    return (
      <AreaChart data={data} margin={margin} {...rest}>
        {common}
        {seriesKeys.map((k, i) => (
          <Area
            key={k}
            type="monotone"
            dataKey={k}
            name={seriesName(k)}
            stackId="1"
            stroke={color(i)}
            fill={color(i)}
            fillOpacity={0.6}
            isAnimationActive={false}
          />
        ))}
      </AreaChart>
    );
  }
  return (
    <BarChart data={data} margin={margin} {...rest}>
      {common}
      {seriesKeys.map((k, i) => (
        <Bar key={k} dataKey={k} name={seriesName(k)} fill={color(i)} isAnimationActive={false} />
      ))}
    </BarChart>
  );
}

// Donut + legend list with value and share (share is display-only).
function PieSpec({ spec, height }) {
  const { x, y, data } = spec;
  const kind = valueKind(y);
  const total = data.reduce((sum, r) => sum + Math.max(r[y], 0), 0);
  return (
    <div>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey={y}
              nameKey={x}
              innerRadius="55%"
              outerRadius="85%"
              paddingAngle={2}
              isAnimationActive={false}
            >
              {data.map((r, i) => (
                <Cell key={String(r[x])} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(v, name) => [formatValue(kind, v), formatCategory(name)]} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 space-y-1">
        {data.map((r, i) => (
          <li key={String(r[x])} className="flex items-center justify-between gap-2 text-[11px]">
            <span className="flex min-w-0 items-center gap-2 text-gray-700">
              <span
                className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{ backgroundColor: PALETTE[i % PALETTE.length] }}
                aria-hidden="true"
              />
              <span className="truncate">{formatCategory(r[x])}</span>
            </span>
            <span className="shrink-0 font-medium tabular-nums text-gray-600">
              {formatValue(kind, r[y])}
              {total > 0 && (
                <span className="text-gray-500"> · {((Math.max(r[y], 0) / total) * 100).toFixed(2)}%</span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const MAX_TABLE_ROWS = 50;

function TableChart({ spec }) {
  const { columns, rows } = spec;
  const shown = rows.slice(0, MAX_TABLE_ROWS);
  const cell = (col, v) => {
    if (typeof v === "number" || (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v)))) {
      return formatValue(valueKind(col), v);
    }
    return formatCategory(v);
  };
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-[11px]">
        <thead>
          <tr className="text-gray-500">
            {columns.map((c) => (
              <th key={c} scope="col" className="pb-1 pr-2 font-medium">
                {humanizeKey(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((r, i) => (
            <tr key={i} className="border-t border-gray-100">
              {columns.map((c) => (
                <td key={c} className="py-1 pr-2 tabular-nums text-gray-700">
                  {cell(c, r[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > MAX_TABLE_ROWS && (
        <p className="mt-1 text-[10px] text-gray-500">Showing first {MAX_TABLE_ROWS} of {rows.length} rows.</p>
      )}
    </div>
  );
}
