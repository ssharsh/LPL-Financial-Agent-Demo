import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { formatCurrency, formatDate } from "../../utils/format.js";

// 12-month portfolio value line chart.
export default function PerformanceChart({ performance }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Value over the past 12 months
      </h3>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={performance} margin={{ top: 5, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef0f2" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(d) =>
                new Date(d).toLocaleDateString("en-US", { month: "short" })
              }
              tick={{ fontSize: 10, fill: "#64748b" }}
              interval="preserveStartEnd"
              minTickGap={20}
            />
            <YAxis
              tickFormatter={(v) => formatCurrency(v, { compact: true })}
              tick={{ fontSize: 10, fill: "#64748b" }}
              width={48}
              domain={["dataMin - 10000", "dataMax + 10000"]}
            />
            <Tooltip
              formatter={(value) => [formatCurrency(value), "Value"]}
              labelFormatter={(label) => formatDate(label)}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#0b5c3f"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
